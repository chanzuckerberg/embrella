import { postFormDataWithProgress, putResource } from '@app/common/queries/fetchResource';
import { ImageRendition } from '@app/common/types/images';
import { testImage } from '@app/common/components/images/testImages';
import { imageSrc, reorderGridImages, uploadGridImage } from './imagesApi';

jest.mock('@app/common/queries/fetchResource', () => ({ postFormDataWithProgress: jest.fn(), putResource: jest.fn() }));

const mockPost = postFormDataWithProgress as jest.Mock;
const mockPut = putResource as jest.Mock;
const file = new File(['x'], 'shot.png', { type: 'image/png' });

describe('uploadGridImage', () => {
  it('posts the file to the grid and returns the image', async () => {
    const image = testImage();
    mockPost.mockResolvedValue({ ok: true, status: 201, body: JSON.stringify(image) });
    const onProgress = jest.fn();

    await expect(uploadGridImage(7, file, onProgress)).resolves.toEqual(image);

    const [url, form, progress] = mockPost.mock.calls[0];
    expect(url).toMatch(/\/cryo_grids\/v1\/grids\/7\/images\/$/);
    expect((form as FormData).get('file')).toBe(file);
    expect(progress).toBe(onProgress);
  });

  it("surfaces the server's message", async () => {
    mockPost.mockResolvedValue({ ok: false, status: 400, body: JSON.stringify({ detail: 'Save a single page.' }) });

    await expect(uploadGridImage(7, file, jest.fn())).rejects.toThrow('Save a single page.');
  });

  it("explains nginx's HTML 413", async () => {
    mockPost.mockResolvedValue({ ok: false, status: 413, body: '<html>Request Entity Too Large</html>' });

    await expect(uploadGridImage(7, file, jest.fn())).rejects.toThrow('File is too large.');
  });
});

describe('reorderGridImages', () => {
  it("surfaces the server's field error", async () => {
    const body = JSON.stringify({ image_ids: ["Can't reorder more than 100 images on one grid."] });
    mockPut.mockResolvedValue({ ok: false, status: 400, text: () => Promise.resolve(body) });

    await expect(reorderGridImages(7, ['a'])).rejects.toThrow("Can't reorder more than 100 images on one grid.");
  });
});

describe('imageSrc', () => {
  it('prefixes the API path with the Django origin', () => {
    expect(imageSrc(testImage({ id: 'x' }), ImageRendition.THUMB)).toMatch(/\/images\/v1\/images\/x\/file\/\?r=thumb$/);
  });
});
