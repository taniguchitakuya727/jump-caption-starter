const fileInput = document.querySelector("#video-file");
const jumpCutForm = document.querySelector("#jump-cut-form");
const selectedFile = document.querySelector("#selected-file");
const processButton = document.querySelector("#process-video");
const refreshButton = document.querySelector("#refresh-ffmpeg");

const ffmpegAvailable = document.querySelector("#ffmpeg-available");
const ffmpegPath = document.querySelector("#ffmpeg-path");
const ffmpegVersion = document.querySelector("#ffmpeg-version");
const ffmpegError = document.querySelector("#ffmpeg-error");
const processLog = document.querySelector("#process-log");
const processError = document.querySelector("#process-error");
const resultLinks = document.querySelector("#result-links");

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

function setProcessing(isProcessing) {
  processButton.disabled = isProcessing;
  processButton.textContent = isProcessing ? "処理中" : "ジャンプカット";
}

function showResultLinks(data) {
  resultLinks.hidden = false;
  resultLinks.innerHTML = "";

  const outputLink = document.createElement("a");
  outputLink.href = data.output_url;
  outputLink.textContent = data.output_file;
  outputLink.target = "_blank";

  const jsonLink = document.createElement("a");
  jsonLink.href = data.silence_json_url;
  jsonLink.textContent = data.silence_json_file;
  jsonLink.target = "_blank";

  resultLinks.append(outputLink, jsonLink);
}

async function processVideo(event) {
  event.preventDefault();

  if (!fileInput.files.length) {
    processError.textContent = "動画ファイルを選択してください。";
    processError.hidden = false;
    return;
  }

  const formData = new FormData(jumpCutForm);
  setProcessing(true);
  processError.hidden = true;
  processError.textContent = "";
  resultLinks.hidden = true;
  resultLinks.innerHTML = "";
  processLog.textContent = "アップロードとFFmpeg処理を開始しました。";

  try {
    const response = await fetch("/api/jump-cut", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    showResultLinks(data);
    const summary = [
      `duration: ${data.duration.toFixed(3)} sec`,
      `silences: ${data.silences.length}`,
      "",
      ...data.logs,
    ];
    processLog.textContent = summary.join("\n");
  } catch (error) {
    processError.textContent = error.message;
    processError.hidden = false;
    processLog.textContent = "処理に失敗しました。";
  } finally {
    setProcessing(false);
  }
}

fileInput.addEventListener("change", updateSelectedFile);
refreshButton.addEventListener("click", loadFFmpegStatus);
jumpCutForm.addEventListener("submit", processVideo);

loadFFmpegStatus();
