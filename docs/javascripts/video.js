function playVideo(facade) {
  const id = facade.dataset.video;
  const poster = facade.querySelector("img");

  const frame = document.createElement("iframe");
  frame.src = `https://www.youtube-nocookie.com/embed/${id}?autoplay=1&rel=0&iv_load_policy=3`;
  frame.title = poster ? poster.alt : "Video";
  frame.allow =
    "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
  frame.referrerPolicy = "strict-origin-when-cross-origin";
  frame.allowFullscreen = true;

  facade.replaceChildren(frame);
  facade.removeAttribute("data-video");
  facade.removeAttribute("role");
  facade.removeAttribute("tabindex");
}

document.addEventListener("click", (event) => {
  const facade = event.target.closest(".video-embed[data-video]");
  if (facade) playVideo(facade);
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Enter" && event.key !== " ") return;
  const facade = event.target.closest(".video-embed[data-video]");
  if (!facade) return;
  event.preventDefault();
  playVideo(facade);
});
