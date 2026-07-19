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
const subtitleEditor = document.querySelector("#subtitle-editor");
const videoPreview = document.querySelector("#video-preview");
const captionOverlay = document.querySelector("#caption-overlay");
const subtitleRows = document.querySelector("#subtitle-rows");
const saveState = document.querySelector("#save-state");
const addSegmentButton = document.querySelector("#add-segment");
const deleteSegmentButton = document.querySelector("#delete-segment");
const splitSegmentButton = document.querySelector("#split-segment");
const mergeSegmentButton = document.querySelector("#merge-segment");
const undoButton = document.querySelector("#undo-edit");
const redoButton = document.querySelector("#redo-edit");
const saveSubtitlesButton = document.querySelector("#save-subtitles");
const searchText = document.querySelector("#search-text");
const replaceText = document.querySelector("#replace-text");
const replaceAllButton = document.querySelector("#replace-all");

let lastOutputFile = null;
let lastSubtitleMetadataFile = null;
let subtitleSegments = [];
let selectedSegmentIndex = 0;
let undoStack = [];
let redoStack = [];
let autosaveTimer = null;

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

function cloneSegments(segments) {
  return segments.map((segment) => ({ ...segment }));
}

function normalizeSegments(segments) {
  return segments
    .map((segment, index) => ({
      index: index + 1,
      start: Number(segment.start),
      end: Number(segment.end),
      text: String(segment.text || ""),
      avg_logprob: segment.avg_logprob ?? null,
      no_speech_prob: segment.no_speech_prob ?? null,
      suspicious: Boolean(segment.suspicious),
    }))
    .sort((a, b) => a.start - b.start)
    .map((segment, index) => ({ ...segment, index: index + 1 }));
}

function formatSeconds(seconds) {
  return Number(seconds).toFixed(3);
}

function setSaveState(text, state = "idle") {
  saveState.textContent = text;
  saveState.dataset.state = state;
}

function pushHistory() {
  undoStack.push(cloneSegments(subtitleSegments));
  if (undoStack.length > 50) {
    undoStack.shift();
  }
  redoStack = [];
}

function markEdited() {
  subtitleSegments = normalizeSegments(subtitleSegments);
  renderSubtitleRows();
  updateCaptionOverlay();
  setSaveState("保存待ち", "dirty");
  window.clearTimeout(autosaveTimer);
  autosaveTimer = window.setTimeout(saveSubtitleEdits, 1200);
}

function selectSegment(index, seek = true) {
  selectedSegmentIndex = Math.max(0, Math.min(index, subtitleSegments.length - 1));
  renderSubtitleRows();
  const segment = subtitleSegments[selectedSegmentIndex];
  if (seek && segment) {
    videoPreview.currentTime = Math.max(0, segment.start);
  }
  updateCaptionOverlay();
}

function updateCaptionOverlay() {
  const currentTime = videoPreview.currentTime || 0;
  const activeIndex = subtitleSegments.findIndex(
    (segment) => currentTime >= segment.start && currentTime <= segment.end,
  );
  const activeSegment = subtitleSegments[activeIndex];

  if (!activeSegment || !activeSegment.text.trim()) {
    captionOverlay.hidden = true;
    captionOverlay.textContent = "";
    return;
  }

  captionOverlay.hidden = false;
  captionOverlay.textContent = activeSegment.text;

  if (activeIndex !== -1 && activeIndex !== selectedSegmentIndex) {
    selectedSegmentIndex = activeIndex;
    renderSubtitleRows();
  }
}

function renderSubtitleRows() {
  subtitleRows.innerHTML = "";
  subtitleSegments.forEach((segment, index) => {
    const row = document.createElement("tr");
    row.dataset.index = String(index);
    if (index === selectedSegmentIndex) {
      row.classList.add("is-selected");
    }
    if (segment.suspicious) {
      row.classList.add("is-suspicious");
    }

    const numberCell = document.createElement("td");
    numberCell.textContent = String(index + 1);

    const startCell = document.createElement("td");
    const startInput = document.createElement("input");
    startInput.type = "number";
    startInput.step = "0.001";
    startInput.min = "0";
    startInput.value = formatSeconds(segment.start);
    startInput.addEventListener("focus", () => selectSegment(index, false));
    startInput.addEventListener("change", () => {
      pushHistory();
      segment.start = Number(startInput.value);
      markEdited();
    });
    startCell.append(startInput);

    const endCell = document.createElement("td");
    const endInput = document.createElement("input");
    endInput.type = "number";
    endInput.step = "0.001";
    endInput.min = "0";
    endInput.value = formatSeconds(segment.end);
    endInput.addEventListener("focus", () => selectSegment(index, false));
    endInput.addEventListener("change", () => {
      pushHistory();
      segment.end = Number(endInput.value);
      markEdited();
    });
    endCell.append(endInput);

    const textCell = document.createElement("td");
    const textArea = document.createElement("textarea");
    textArea.value = segment.text;
    textArea.rows = 2;
    textArea.addEventListener("focus", () => selectSegment(index, false));
    textArea.addEventListener("change", () => {
      pushHistory();
      segment.text = textArea.value;
      markEdited();
    });
    textCell.append(textArea);

    row.addEventListener("click", (event) => {
      if (event.target === row || event.target === numberCell) {
        selectSegment(index);
      }
    });

    row.append(numberCell, startCell, endCell, textCell);
    subtitleRows.append(row);
  });
}

function openSubtitleEditor(data) {
  lastSubtitleMetadataFile = data.metadata_file;
  subtitleSegments = normalizeSegments(data.segments || []);
  selectedSegmentIndex = 0;
  undoStack = [];
  redoStack = [];
  videoPreview.src = `/outputs/${lastOutputFile}`;
  subtitleEditor.hidden = false;
  renderSubtitleRows();
  updateCaptionOverlay();
  setSaveState("保存済み", "saved");
}

async function saveSubtitleEdits() {
  if (!lastSubtitleMetadataFile) {
    return;
  }

  setSaveState("保存中", "saving");
  try {
    const response = await fetch(`/api/subtitles/${lastSubtitleMetadataFile}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ segments: subtitleSegments }),
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }
    subtitleSegments = normalizeSegments(data.segments);
    showSubtitleLinks(data);
    renderSubtitleRows();
    updateCaptionOverlay();
    setSaveState("保存済み", "saved");
  } catch (error) {
    processError.textContent = error.message;
    processError.hidden = false;
    setSaveState("保存失敗", "error");
  }
}

function addSegment() {
  pushHistory();
  const current = subtitleSegments[selectedSegmentIndex];
  const start = current ? current.end : 0;
  subtitleSegments.splice(selectedSegmentIndex + 1, 0, {
    index: selectedSegmentIndex + 2,
    start,
    end: start + 2,
    text: "",
    avg_logprob: null,
    no_speech_prob: null,
    suspicious: true,
  });
  selectedSegmentIndex += 1;
  markEdited();
}

function deleteSegment() {
  if (!subtitleSegments.length) return;
  pushHistory();
  subtitleSegments.splice(selectedSegmentIndex, 1);
  selectedSegmentIndex = Math.max(0, selectedSegmentIndex - 1);
  markEdited();
}

function splitSegment() {
  const segment = subtitleSegments[selectedSegmentIndex];
  if (!segment) return;
  pushHistory();
  const originalEnd = segment.end;
  const midpoint = (segment.start + segment.end) / 2;
  const textMidpoint = Math.ceil(segment.text.length / 2);
  const firstText = segment.text.slice(0, textMidpoint).trim();
  const secondText = segment.text.slice(textMidpoint).trim();
  segment.end = midpoint;
  segment.text = firstText;
  subtitleSegments.splice(selectedSegmentIndex + 1, 0, {
    ...segment,
    start: midpoint,
    end: originalEnd,
    text: secondText,
    suspicious: true,
  });
  markEdited();
}

function mergeSegment() {
  const segment = subtitleSegments[selectedSegmentIndex];
  const nextSegment = subtitleSegments[selectedSegmentIndex + 1];
  if (!segment || !nextSegment) return;
  pushHistory();
  segment.end = nextSegment.end;
  segment.text = `${segment.text}${segment.text && nextSegment.text ? "\n" : ""}${nextSegment.text}`;
  segment.suspicious = segment.suspicious || nextSegment.suspicious;
  subtitleSegments.splice(selectedSegmentIndex + 1, 1);
  markEdited();
}

function undoEdit() {
  if (!undoStack.length) return;
  redoStack.push(cloneSegments(subtitleSegments));
  subtitleSegments = undoStack.pop();
  markEdited();
}

function redoEdit() {
  if (!redoStack.length) return;
  undoStack.push(cloneSegments(subtitleSegments));
  subtitleSegments = redoStack.pop();
  markEdited();
}

function replaceAllText() {
  const needle = searchText.value;
  if (!needle) return;
  pushHistory();
  const replacement = replaceText.value;
  subtitleSegments = subtitleSegments.map((segment) => ({
    ...segment,
    text: segment.text.split(needle).join(replacement),
  }));
  markEdited();
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
    openSubtitleEditor(data);
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
addSegmentButton.addEventListener("click", addSegment);
deleteSegmentButton.addEventListener("click", deleteSegment);
splitSegmentButton.addEventListener("click", splitSegment);
mergeSegmentButton.addEventListener("click", mergeSegment);
undoButton.addEventListener("click", undoEdit);
redoButton.addEventListener("click", redoEdit);
saveSubtitlesButton.addEventListener("click", saveSubtitleEdits);
replaceAllButton.addEventListener("click", replaceAllText);
videoPreview.addEventListener("timeupdate", updateCaptionOverlay);
videoPreview.addEventListener("seeked", updateCaptionOverlay);

loadFFmpegStatus();
loadWhisperStatus();
