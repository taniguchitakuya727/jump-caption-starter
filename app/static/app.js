const fileInput = document.querySelector("#video-file");
const jumpCutForm = document.querySelector("#jump-cut-form");
const subtitleForm = document.querySelector("#subtitle-form");
const selectedFile = document.querySelector("#selected-file");
const processButton = document.querySelector("#process-video");
const subtitleButton = document.querySelector("#generate-subtitles");
const refreshButton = document.querySelector("#refresh-ffmpeg");
const refreshWhisperButton = document.querySelector("#refresh-whisper");

const ffmpegAvailable = document.querySelector("#ffmpeg-available");
const ffmpegPath = document.querySelector("#ffmpeg-path");
const ffmpegVersion = document.querySelector("#ffmpeg-version");
const ffmpegError = document.querySelector("#ffmpeg-error");
const whisperAvailable = document.querySelector("#whisper-available");
const whisperModel = document.querySelector("#whisper-model");
const whisperLanguage = document.querySelector("#whisper-language");
const whisperNote = document.querySelector("#whisper-note");
const processLog = document.querySelector("#process-log");
const processError = document.querySelector("#process-error");
const resultLinks = document.querySelector("#result-links");
const subtitleLinks = document.querySelector("#subtitle-links");

let lastOutputFile = null;

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

async function loadWhisperStatus() {
  whisperAvailable.textContent = "確認中";
  whisperNote.hidden = true;
  whisperNote.textContent = "";

  try {
    const response = await fetch("/api/whisper");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    whisperAvailable.textContent = data.available ? "利用可能" : "未インストール";
    whisperAvailable.dataset.state = data.available ? "ok" : "missing";
    whisperModel.textContent = data.default_model;
    whisperLanguage.textContent = data.default_language;
    whisperNote.textContent = data.note;
    whisperNote.hidden = false;
  } catch (error) {
    whisperAvailable.textContent = "確認失敗";
    whisperAvailable.dataset.state = "missing";
    whisperNote.textContent = error.message;
    whisperNote.hidden = false;
  }
}

function setProcessing(isProcessing) {
  processButton.disabled = isProcessing;
  processButton.textContent = isProcessing ? "処理中" : "ジャンプカット";
}

function setSubtitleProcessing(isProcessing) {
  subtitleButton.disabled = isProcessing;
  subtitleButton.textContent = isProcessing ? "生成中" : "字幕生成";
}

function makeLink(href, text) {
  const link = document.createElement("a");
  link.href = href;
  link.textContent = text;
  link.target = "_blank";
  return link;
}

function showResultLinks(data) {
  resultLinks.hidden = false;
  resultLinks.innerHTML = "";
  resultLinks.append(
    makeLink(data.output_url, data.output_file),
    makeLink(data.silence_json_url, data.silence_json_file),
  );
}

function showSubtitleLinks(data) {
  subtitleLinks.hidden = false;
  subtitleLinks.innerHTML = "";
  subtitleLinks.append(
    makeLink(data.srt_url, data.srt_file),
    makeLink(data.txt_url, data.txt_file),
    makeLink(data.metadata_url, data.metadata_file),
  );
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
  subtitleForm.hidden = true;
  subtitleLinks.hidden = true;
  subtitleLinks.innerHTML = "";

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
    lastOutputFile = data.output_file;
    subtitleForm.hidden = false;
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

async function generateSubtitles(event) {
  event.preventDefault();

  if (!lastOutputFile) {
    processError.textContent = "先にジャンプカットを実行してください。";
    processError.hidden = false;
    return;
  }

  const formData = new FormData(subtitleForm);
  formData.append("filename", lastOutputFile);
  const language = formData.get("language");
  if (language === "auto") {
    formData.set("language", "");
  }

  setSubtitleProcessing(true);
  processError.hidden = true;
  processError.textContent = "";
  subtitleLinks.hidden = true;
  subtitleLinks.innerHTML = "";
  processLog.textContent = "Whisper字幕生成を開始しました。初回はモデルの取得に時間がかかることがあります。";

  try {
    const response = await fetch("/api/subtitles", {
      method: "POST",
      body: formData,
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    showSubtitleLinks(data);
    const suspiciousCount = data.segments.filter((segment) => segment.suspicious).length;
    const summary = [
      `subtitle segments: ${data.segments.length}`,
      `suspicious segments: ${suspiciousCount}`,
      "",
      ...data.logs,
    ];
    processLog.textContent = summary.join("\n");
  } catch (error) {
    processError.textContent = error.message;
    processError.hidden = false;
    processLog.textContent = "字幕生成に失敗しました。";
  } finally {
    setSubtitleProcessing(false);
  }
}

fileInput.addEventListener("change", updateSelectedFile);
refreshButton.addEventListener("click", loadFFmpegStatus);
refreshWhisperButton.addEventListener("click", loadWhisperStatus);
jumpCutForm.addEventListener("submit", processVideo);
subtitleForm.addEventListener("submit", generateSubtitles);

loadFFmpegStatus();
loadWhisperStatus();
