import logging
from abc import abstractmethod
from typing import Literal, Optional, Tuple

import numpy as np
import dask.array as da
import zarr
import fsspec
from scipy.signal import find_peaks
from sklearn.mixture import GaussianMixture

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_zarr_data(zarr_url: str, max_samples: int = 100_000) -> np.ndarray:
    """
    Load data from a Zarr store (HTTP or local) and return a 1D sample array.
    """
    # Try HTTP(S) via fsspec first
    if zarr_url.startswith(("http://", "https://")):
        try:
            LOGGER.info(f"Attempting HTTP access via fsspec: {zarr_url}")
            mapper = fsspec.get_mapper(zarr_url)
            root = zarr.open(mapper, mode="r")
            data = _extract_data_from_store(root, max_samples)
            if data is not None:
                return data
        except Exception as e:
            LOGGER.warning(f"HTTP access failed: {e}")

    # Fallback to direct zarr.open (for local paths or when mapper fails)
    try:
        LOGGER.info(f"Attempting direct zarr.open: {zarr_url}")
        root = zarr.open(zarr_url, mode="r")
        data = _extract_data_from_store(root, max_samples)
        if data is not None:
            return data
    except Exception as e:
        LOGGER.warning(f"Direct zarr.open failed: {e}")

    raise RuntimeError(f"Could not load Zarr data from {zarr_url}")


def _extract_data_from_store(store_obj, max_samples: int) -> Optional[np.ndarray]:
    """
    Given a Zarr Group or Array, pick the correct array:
      - If Group has 'multiscales' in attrs, use the first dataset path;
      - Else if Group, pick the first array key;
      - Else treat it as an Array.
    Then sample and return up to max_samples.
    """
    try:
        # 1) If it's a group, handle multiscales or pick first array
        if isinstance(store_obj, zarr.hierarchy.Group):
            if "multiscales" in store_obj.attrs:
                ms = store_obj.attrs["multiscales"]
                # take the first multiscale spec and its first dataset
                path = ms[0]["datasets"][0]["path"]
                LOGGER.info(f"Using multiscale dataset at path '{path}'")
                arr = store_obj[path]
            else:
                keys = list(store_obj.array_keys())
                if not keys:
                    LOGGER.warning("No arrays found in Zarr group.")
                    return None
                LOGGER.info(f"No multiscales; loading array '{keys[0]}'")
                arr = store_obj[keys[0]]
        else:
            # Already an Array
            arr = store_obj  # type: ignore

        # 2) Convert to dask.Array if necessary
        if not isinstance(arr, da.Array):
            arr = da.from_array(arr)

        # 3) For 3D, take central z-slice; else flatten directly
        if arr.ndim == 3:
            zc = arr.shape[0] // 2
            plane = arr[zc, :, :]
            flat = plane.flatten()
        else:
            flat = arr.flatten()

        # 4) Random sampling if too large
        total = len(flat)
        if total > max_samples:
            idx = np.random.choice(total, max_samples, replace=False)
            sample = flat[idx]
        else:
            sample = flat.compute()

        return sample

    except Exception as e:
        LOGGER.warning(f"Error extracting data from store: {e}")
        return None


def compute_contrast_limits(
    data: np.ndarray,
    method: Literal["gmm", "cdf"] = "gmm",
    z_radius: Optional[int] = None,
    downsampling_ratio: Optional[float] = 0.3,
) -> Tuple[float, float]:
    """Dispatch to GMM or CDF-based contrast limit calculator."""
    Calculator = GMMContrastLimitCalculator if method == "gmm" else CDFContrastLimitCalculator
    if z_radius == "auto":
        z_radius = 15 if method == "gmm" else 5
    num_samples = None if downsampling_ratio is None else int(data.size * downsampling_ratio)
    return Calculator(data, z_radius=z_radius, num_samples=num_samples).compute_contrast_limit()


def _restrict_volume_around_central_z_slice(volume, central_z_slice=None, z_radius=5):
    """Helper: crop a 3D volume around its central slice."""
    if volume.ndim == 2:
        return volume
    cz = int(central_z_slice or (volume.shape[0] // 2))
    if z_radius is None:
        return volume
    zmin = max(0, cz - z_radius)
    zmax = min(volume.shape[0], cz + z_radius + 1)
    return volume[zmin:zmax]


def _take_random_samples_from_volume(volume, num_samples=None):
    """Flatten and random-sample a volume if needed."""
    flat = volume.flatten()
    total = len(flat)
    if num_samples is None or num_samples >= total:
        return flat
    rng = np.random.default_rng(42)
    return rng.choice(flat, num_samples, replace=False)


class ContrastLimitCalculator:
    """Base class. Subclasses must implement compute_contrast_limit()."""

    def __init__(self, volume, z_radius=None, num_samples=None, central_z_slice=None):
        vol = _restrict_volume_around_central_z_slice(volume, central_z_slice, z_radius)
        self.volume = _take_random_samples_from_volume(vol, num_samples)

    @abstractmethod
    def compute_contrast_limit(self) -> Tuple[float, float]:
        ...


class PercentileContrastLimitCalculator(ContrastLimitCalculator):
    def compute_contrast_limit(self, low_percentile=1.0, high_percentile=99.0):
        lo = np.percentile(self.volume, low_percentile)
        hi = np.percentile(self.volume, high_percentile)
        return float(lo), float(hi)


class GMMContrastLimitCalculator(ContrastLimitCalculator):
    def compute_contrast_limit(
        self,
        low_variance_mult: float = 3.0,
        high_variance_mult: float = 0.5,
        max_components: int = 3,
    ) -> Tuple[float, float]:
        sample = self.volume.reshape(-1, 1)
        # pick best GMM by BIC
        bics = []
        for n in range(1, max_components + 1):
            gm = GaussianMixture(n_components=n, random_state=42)
            try:
                gm.fit(sample)
                bics.append((gm.bic(sample), n))
            except:
                bics.append((np.inf, n))
        _, best_n = min(bics)
        # re-fit best model
        gm = GaussianMixture(n_components=best_n, random_state=42, max_iter=300)
        gm.fit(sample)
        means = gm.means_.flatten()
        stds = np.sqrt(gm.covariances_.flatten())
        vm = means[np.argmin(np.abs(means - np.mean(sample)))]
        sv = stds[np.argmin(np.abs(means - np.mean(sample)))]
        low_m, high_m = {1: (2.0, 0.5), 2: (2.2, 0.65), 3: (3.0, 0.8)}.get(best_n, (3.0, 0.5))
        lo = max(vm - low_m * sv, np.min(sample))
        hi = min(vm + high_m * sv, np.max(sample))
        return float(lo), float(hi)


class CDFContrastLimitCalculator(ContrastLimitCalculator):
    def calculate_cdf(self, n_bins=512):
        mn, mx = np.min(self.volume), np.max(self.volume)
        h, edges = np.histogram(self.volume, bins=n_bins, range=[mn, mx])
        cdf = np.cumsum(h) / h.sum()
        grad = np.gradient(cdf)
        xs = np.linspace(mn, mx, n_bins)
        return cdf, edges, grad, xs

    def compute_contrast_limit(self, gradient_threshold=0.3):
        _, edges, grad, _ = self.calculate_cdf()
        peak = np.argmax(grad)
        start = np.where(grad > gradient_threshold * grad[peak])[0][0]
        end = np.where(grad[peak:] < gradient_threshold * grad[peak])[0][0] + peak
        lo, hi = edges[start], edges[end]
        return float(max(lo, np.min(self.volume))), float(min(hi, np.max(self.volume)))


def compute_optimal_contrast_limits(zarr_url: str, method: str = "gmm") -> Tuple[float, float]:
    """High-level entry: load the data then dispatch to the calculator."""
    try:
        data = load_zarr_data(zarr_url)
        return compute_contrast_limits(data, method=method)
    except Exception as e:
        LOGGER.error(f"Failed overall: {e}")
        return -0.05, 0.05


def main():
    url = "https://czii-onsite.czbiohub.org/krios1.processing/aretomo3/25jun02a/run001/vol003/Position_114_8_Vol.zarr/"
    print("Computing contrast limits for:", url)
    limits = compute_optimal_contrast_limits(url, method="gmm")
    print("Contrast limits:", limits)


if __name__ == "__main__":
    main()