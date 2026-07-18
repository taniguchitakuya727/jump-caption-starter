const fileInput = document.querySelector("#video-file");
const selectedFile = document.querySelector("#selected-file");
const refreshButton = document.querySelector("#refresh-ffmpeg");

const ffmpegAvailable = document.querySelector("#ffmpeg-available");
const ffmpegPath = document.querySelector("#ffmpeg-path");
const ffmpegVersion = document.querySelector("#ffmpeg-version");
const ffmpegError = document.querySelector("#ffmpeg-error");

function formatBytes(bytes) {
  if (bytes === 0) return "0 B";

  const units = ["B", "KB", "MB", "GB"];
  const exponent = Math.min(
    Math.floor(Math.log(bytes) / Math.log(1024)),
    units.length - 1,
  );
  const value = bytes / 1024 ** exponent;
  return `${value.toFixed(value >= 10 || exponent === 0 ? 0 : 1)} ${units[exponent]}`;
}

function updateSelectedFile() {
  const file = fileInput.files[0];
  selectedFile.textContent = file
    ? `${file.name} (${formatBytes(file.size)})`
    : "未選択";
}

async function loadFFmpegStatus() {
  ffmpegAvailable.textContent = "確認中";
  ffmpegPath.textContent = "-";
  ffmpegVersion.textContent = "-";
  ffmpegError.hidden = true;
  ffmpegError.textContent = "";

  try {
    const response = await fetch("/api/ffmpeg");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    ffmpegAvailable.textContent = data.available ? "利用可能" : "見つかりません";
    ffmpegAvailable.dataset.state = data.available ? "ok" : "missing";
    ffmpegPath.textContent = data.path || "-";
    ffmpegVersion.textContent = data.version || "-";

    if (data.error) {
      ffmpegError.textContent = data.error;
      ffmpegError.hidden = false;
    }
  } catch (error) {
    ffmpegAvailable.textContent = "確認失敗";
    ffmpegAvailable.dataset.state = "missing";
    ffmpegError.textContent = error.message;
    ffmpegError.hidden = false;
  }
}

fileInput.addEventListener("change", updateSelectedFile);
refreshButton.addEventListener("click", loadFFmpegStatus);

loadFFmpegStatus();

