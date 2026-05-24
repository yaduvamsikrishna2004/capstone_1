import { uploadFiles } from "./api.js";
import { formatBytes, uid } from "./utils.js";

const ALLOWED_EXTENSIONS = [".pdf", ".docx", ".txt"];

function extensionAllowed(name = "") {
  return ALLOWED_EXTENSIONS.some((ext) => name.toLowerCase().endsWith(ext));
}

export function createUploadController({
  dropzoneEl,
  fileInputEl,
  uploadQueueEl,
  uploadNowBtn,
  clearQueueBtn,
  notifier,
  onUploadComplete,
  onStatusChange,
}) {
  let queue = [];

  function renderQueue() {
    uploadQueueEl.innerHTML = "";
    if (!queue.length) {
      uploadQueueEl.innerHTML = "<div class=\"history-item\"><small>No files selected.</small></div>";
      onStatusChange?.(0);
      return;
    }

    queue.forEach((item) => {
      const article = document.createElement("article");
      article.className = "upload-item";
      article.dataset.id = item.id;
      article.innerHTML = `
        <div>
          <strong title="${item.file.name}">${item.file.name}</strong>
          <small>${formatBytes(item.file.size)}</small>
          <div class="progress-track"><div class="progress-bar" style="width:${item.progress}%"></div></div>
          <div class="upload-status ${item.statusClass}">${item.status}</div>
        </div>
        <div class="upload-item-actions">
          <button class="upload-remove" type="button">Remove</button>
        </div>
      `;
      article.querySelector(".upload-remove").addEventListener("click", () => {
        queue = queue.filter((entry) => entry.id !== item.id);
        renderQueue();
      });
      uploadQueueEl.appendChild(article);
    });
    onStatusChange?.(queue.length);
  }

  function pushFiles(fileList) {
    const accepted = [];
    const rejected = [];
    Array.from(fileList).forEach((file) => {
      if (!extensionAllowed(file.name)) {
        rejected.push(file.name);
        return;
      }
      accepted.push({
        id: uid("upload"),
        file,
        progress: 0,
        status: "Ready to upload",
        statusClass: "",
      });
    });

    if (rejected.length) {
      notifier.error(`Unsupported files skipped: ${rejected.join(", ")}`);
    }
    if (accepted.length) {
      queue = [...queue, ...accepted];
      renderQueue();
    }
  }

  async function runUpload() {
    if (!queue.length) {
      notifier.info("Select at least one file before uploading.");
      return;
    }

    uploadNowBtn.disabled = true;
    const files = queue.map((item) => item.file);

    try {
      const response = await uploadFiles(files, (progress) => {
        queue = queue.map((item) => ({
          ...item,
          progress,
          status: progress < 100 ? "Uploading..." : "Upload complete",
          statusClass: progress < 100 ? "" : "success",
        }));
        renderQueue();
      });

      const now = Date.now();
      queue = queue.map((item) => ({
        ...item,
        progress: 100,
        status: "Successfully indexed",
        statusClass: "success",
        uploadedAt: now,
      }));
      renderQueue();
      notifier.success(`${response.files_processed} file(s) uploaded and indexed.`);
      onUploadComplete?.(
        queue.map((item) => ({
          name: item.file.name,
          size: item.file.size,
          uploadedAt: item.uploadedAt || now,
        })),
        response,
      );
      queue = [];
      renderQueue();
    } catch (error) {
      queue = queue.map((item) => ({
        ...item,
        status: "Upload failed",
        statusClass: "error",
      }));
      renderQueue();
      notifier.error(error.message || "Upload failed.");
    } finally {
      uploadNowBtn.disabled = false;
    }
  }

  dropzoneEl.addEventListener("click", () => fileInputEl.click());

  dropzoneEl.addEventListener("dragover", (event) => {
    event.preventDefault();
    dropzoneEl.classList.add("drag-active");
  });

  dropzoneEl.addEventListener("dragleave", () => {
    dropzoneEl.classList.remove("drag-active");
  });

  dropzoneEl.addEventListener("drop", (event) => {
    event.preventDefault();
    dropzoneEl.classList.remove("drag-active");
    if (event.dataTransfer?.files?.length) {
      pushFiles(event.dataTransfer.files);
    }
  });

  fileInputEl.addEventListener("change", (event) => {
    const target = event.target;
    if (target.files?.length) {
      pushFiles(target.files);
      target.value = "";
    }
  });

  uploadNowBtn.addEventListener("click", runUpload);
  clearQueueBtn.addEventListener("click", () => {
    queue = [];
    renderQueue();
  });

  renderQueue();

  return {
    addFiles: pushFiles,
    getQueue: () => queue,
  };
}
