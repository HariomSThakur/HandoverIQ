document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".flash-close").forEach((button) => {
    button.addEventListener("click", () => button.closest(".flash")?.remove());
  });

  const fileInput = document.querySelector("#source-file");
  if (fileInput) {
    fileInput.addEventListener("change", () => {
      const chosen = fileInput.files?.[0];
      const strong = fileInput.closest(".dropzone")?.querySelector("strong");
      if (chosen && strong) strong.textContent = chosen.name;
    });
  }
});
