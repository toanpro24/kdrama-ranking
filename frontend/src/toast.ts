type ToastType = "success" | "error" | "info";

let container: HTMLDivElement | null = null;

function getContainer(): HTMLDivElement {
  if (container) return container;
  container = document.createElement("div");
  container.className = "toast-container";
  document.body.appendChild(container);
  return container;
}

function removeToast(el: HTMLDivElement) {
  el.classList.add("toast-exit");
  setTimeout(() => el.remove(), 300);
}

export function toast(message: string, type: ToastType = "info", duration = 3000) {
  const c = getContainer();
  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span class="toast-icon">${type === "success" ? "✓" : type === "error" ? "✕" : "i"}</span><span class="toast-msg">${message}</span>`;
  el.addEventListener("click", () => removeToast(el));
  c.appendChild(el);
  requestAnimationFrame(() => el.classList.add("toast-enter"));
  setTimeout(() => removeToast(el), duration);
}

toast.success = (msg: string) => toast(msg, "success");
toast.error = (msg: string) => toast(msg, "error", 5000);
toast.info = (msg: string) => toast(msg, "info");
