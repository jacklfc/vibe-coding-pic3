<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue';

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001').replace(/\/$/, '');
const DEFAULT_MATERIAL_FILES = [
  '0a86a3a4b1504bbaab400b12a8f22633.jpg',
  '0cd9eaf3bb774c0eabb13212c6856749.jpg',
  '3b3cf348c64a4fff8a36a97c1f95be39.jpg',
];
const objectUrlCache = new Map();

const keyword = ref('禾木');
const images = ref([null, null, null]);
const imageTransforms = ref([
  { x: 0, y: 0, scale: 1 },
  { x: 0, y: 0, scale: 1 },
  { x: 0, y: 0, scale: 1 },
]);
const report = ref('');
const isBusy = ref(false);
const uploadIds = ref([]);
const copySets = ref([]);
const selectedCopyId = ref(1);
const resultUrl = ref('');
const replaceInput = ref(null);
const selectedCopy = ref({
  id: 1,
  lines_cn: ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
  lines_en: ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
  recommend: true,
});
const customCopyText = ref('');
const selectedSegment = ref(2);
const bottomSheetOpen = ref(false);
const replacePulse = ref(false);
const previewOverlayVisible = ref(false);
const dragImageState = ref({});
const dragSlotIndex = ref(null);

const cropDrafts = ref([
  { x: 50, y: 50, zoom: 1 },
  { x: 50, y: 50, zoom: 1 },
  { x: 50, y: 50, zoom: 1 },
]);
const cropDragState = ref(null);

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function resetCropDrafts() {
  cropDrafts.value = Array.from({ length: 3 }, () => ({ x: 50, y: 50, zoom: 1 }));
}

function resetImageTransforms() {
  imageTransforms.value = Array.from({ length: images.value.length }, () => ({ x: 0, y: 0, scale: 1, rotation: 0 }));
}

function normalizeTransform(transform = {}) {
  return {
    x: Number(transform.x || 0),
    y: Number(transform.y || 0),
    scale: Number(transform.scale || 1),
    rotation: Number(transform.rotation || 0),
  };
}

function clampTransformForElement(element, transform) {
  const rect = element.parentElement?.getBoundingClientRect?.();
  if (!rect) {
    return normalizeTransform(transform);
  }

  const displayWidth = rect.width * transform.scale;
  const displayHeight = rect.height * transform.scale;
  const maxX = Math.max(0, (displayWidth - rect.width) / 2);
  const maxY = Math.max(0, (displayHeight - rect.height) / 2);

const next = normalizeTransform(transform);
const clampedX = clamp(next.x, -maxX, maxX);
const clampedY = clamp(next.y, -maxY, maxY);

return {
  ...next,
  x: clampedX,
  y: clampedY,
  scale: clamp(next.scale, 0.5, 6),
};
}

function selectSegment(index) {
  selectedSegment.value = index;
  bottomSheetOpen.value = true;
}

function toggleBottomSheet() {
  const nextState = !bottomSheetOpen.value;
  bottomSheetOpen.value = nextState;
  if (!nextState) {
    selectedSegment.value = null;
  }
}

function getObjectUrl(file) {
  if (!file) return '';
  const cacheKey = `${file.name}:${file.size}:${file.lastModified}`;
  if (!objectUrlCache.has(cacheKey)) {
    objectUrlCache.set(cacheKey, URL.createObjectURL(file));
  }
  return objectUrlCache.get(cacheKey);
}

function cropStyleFor(index) {
  const draft = cropDrafts.value[index] || { x: 50, y: 50, zoom: 1 };
  const widthPct = clamp(100 / draft.zoom, 35, 100);
  const heightPct = widthPct / 2.25;
  const left = clamp(draft.x - widthPct / 2, 0, 100 - widthPct);
  const top = clamp(draft.y - heightPct / 2, 0, 100 - heightPct);

  return {
    width: `${widthPct}%`,
    height: `${heightPct}%`,
    left: `${left}%`,
    top: `${top}%`,
  };
}

function onFilePicked(event) {
  const incoming = Array.from(event.target.files || []).filter((file) => file && file.type.startsWith('image/'));
  if (!incoming.length) {
    report.value = '错误：请上传合法的图片文件。';
    return;
  }

  if (incoming.length === 1 && event.target === replaceInput.value) {
    images.value[selectedSegment.value] = incoming[0];
    report.value = `已替换第 ${selectedSegment.value + 1} 张素材图。`;
  } else {
    images.value = [incoming[0] || null, incoming[1] || null, incoming[2] || null];
    report.value = '';
  }

  resetCropDrafts();
  resetImageTransforms();
  event.target.value = '';
}

function setSelectedCopy(item) {
  selectedCopyId.value = item.id;
  selectedCopy.value = {
    ...item,
    lines_cn: [...(item.lines_cn || [])],
    lines_en: [...(item.lines_en || [])],
  };
  customCopyText.value = (selectedCopy.value.lines_cn || []).slice(0, 3).join('\n');
}

function handleReplace() {
  replacePulse.value = true;
  bottomSheetOpen.value = true;
  replaceInput.value?.click();
  setTimeout(() => {
    replacePulse.value = false;
  }, 500);
}

function copyCurrentText() {
  const text = selectedCopy.value.lines_cn?.slice(0, 3).join('\n') || customCopyText.value;
  if (!text) return;
  navigator.clipboard?.writeText(text).catch(() => {});
}

function getImageTransformStyle(index) {
  const transform = normalizeTransform(imageTransforms.value[index]);
  return {
    transform: `translate(${transform.x}px, ${transform.y}px) rotate(${transform.rotation}deg) scale(${transform.scale})`,
    transformOrigin: 'center center',
  };
}

function startImageTransform(index, event) {
  if (!images.value[index]) return;
  selectSegment(index);

  const gesture = {
    pointerIds: new Map([[event.pointerId, { x: event.clientX, y: event.clientY }]]),
    startX: event.clientX,
    startY: event.clientY,
    originX: (imageTransforms.value[index] || { x: 0, y: 0, scale: 1, rotation: 0 }).x,
    originY: (imageTransforms.value[index] || { x: 0, y: 0, scale: 1, rotation: 0 }).y,
    originScale: (imageTransforms.value[index] || { x: 0, y: 0, scale: 1, rotation: 0 }).scale,
    originRotation: (imageTransforms.value[index] || { x: 0, y: 0, scale: 1, rotation: 0 }).rotation,
    pinchDistance: 0,
    pinchAngle: 0,
    pinchCenterX: event.clientX,
    pinchCenterY: event.clientY,
  };

  dragImageState.value[index] = gesture;
  event.currentTarget.setPointerCapture?.(event.pointerId);
  event.preventDefault();
}

function moveImageTransform(event) {
  const gesture = dragImageState.value[event.currentTarget.dataset.index];
  if (!gesture) return;

  gesture.pointerIds.set(event.pointerId, { x: event.clientX, y: event.clientY });

  const nextTransform = normalizeTransform(imageTransforms.value[event.currentTarget.dataset.index]);
  if (gesture.pointerIds.size === 1) {
    const dx = event.clientX - gesture.startX;
    const dy = event.clientY - gesture.startY;
    const bounded = clampTransformForElement(event.currentTarget, {
      ...nextTransform,
      x: gesture.originX + dx,
      y: gesture.originY + dy,
    });
    imageTransforms.value[event.currentTarget.dataset.index] = bounded;
    return;
  }

  if (gesture.pointerIds.size >= 2) {
    const points = [...gesture.pointerIds.values()];
    const [first, second] = points;
    const centerX = (first.x + second.x) / 2;
    const centerY = (first.y + second.y) / 2;
    const distance = Math.hypot(second.x - first.x, second.y - first.y);
    const angle = Math.atan2(second.y - first.y, second.x - first.x) * (180 / Math.PI);

    if (!gesture.pinchDistance || !gesture.pinchAngle) {
      gesture.pinchDistance = distance;
      gesture.pinchAngle = angle;
      gesture.pinchCenterX = centerX;
      gesture.pinchCenterY = centerY;
    }

    const scaleFactor = gesture.pinchDistance ? distance / gesture.pinchDistance : 1;
    const rotationDelta = angle - gesture.pinchAngle;
    const bounded = clampTransformForElement(event.currentTarget, {
      ...nextTransform,
      x: gesture.originX + (centerX - gesture.pinchCenterX),
      y: gesture.originY + (centerY - gesture.pinchCenterY),
      scale: clamp(gesture.originScale * scaleFactor, 0.5, 6),
      rotation: gesture.originRotation + rotationDelta,
    });
    imageTransforms.value[event.currentTarget.dataset.index] = bounded;
  }
}

function stopImageTransform(event) {
  const index = Number(event?.currentTarget?.dataset?.index ?? event?.target?.dataset?.index ?? -1);
  if (index >= 0) {
    delete dragImageState.value[index];
  }
}

function onImageWheel(index, event) {
  if (!images.value[index]) return;
  event.preventDefault();
  const next = normalizeTransform(imageTransforms.value[index]);
  const delta = event.deltaY < 0 ? 0.09 : -0.09;
  next.scale = clamp(Number((next.scale + delta).toFixed(2)), 0.5, 6);
  imageTransforms.value[index] = clampTransformForElement(event.currentTarget.parentElement, next);
}

function onSlotDragStart(index) {
  dragSlotIndex.value = index;
}

function onSlotDrop(targetIndex) {
  if (dragSlotIndex.value === null || dragSlotIndex.value === targetIndex) return;
  const nextImages = [...images.value];
  const nextTransforms = [...imageTransforms.value];
  const fromIndex = dragSlotIndex.value;
  const [movedImage] = nextImages.splice(fromIndex, 1);
  const [movedTransform] = nextTransforms.splice(fromIndex, 1);
  nextImages.splice(targetIndex, 0, movedImage);
  nextTransforms.splice(targetIndex, 0, movedTransform);
  images.value = nextImages;
  imageTransforms.value = nextTransforms;
  selectedSegment.value = targetIndex;
  dragSlotIndex.value = null;
}

function startCropDrag(index, event) {
  if (!images.value[index]) return;
  cropDragState.value = {
    index,
    startX: event.clientX,
    startY: event.clientY,
    originX: cropDrafts.value[index].x,
    originY: cropDrafts.value[index].y,
  };
  event.target.setPointerCapture?.(event.pointerId);
}

function onCropDrag(event) {
  if (!cropDragState.value) return;
  const { index, startX, startY, originX, originY } = cropDragState.value;
  const draft = cropDrafts.value[index] || { x: 50, y: 50, zoom: 1 };
  draft.x = clamp(originX + ((event.clientX - startX) / 500) * 100, 0, 100);
  draft.y = clamp(originY + ((event.clientY - startY) / 500) * 100, 0, 100);
  cropDrafts.value[index] = draft;
}

function stopCropDrag() {
  cropDragState.value = null;
}

function onWheelZoom(index, event) {
  if (!images.value[index]) return;
  const draft = cropDrafts.value[index] || { x: 50, y: 50, zoom: 1 };
  const delta = event.deltaY < 0 ? 0.12 : -0.12;
  draft.zoom = clamp(Number((draft.zoom + delta).toFixed(2)), 0.8, 2.4);
  cropDrafts.value[index] = draft;
}

async function fetchJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { Accept: 'application/json', ...(options.headers || {}) },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.message || payload?.error || '请求失败');
  }
  return payload;
}

async function uploadAllImages() {
  const uploaded = [];
  for (const image of images.value) {
    if (!image) throw new Error('请先上传 3 张素材图。');

    const formData = new FormData();
    formData.append('file', image);
    const payload = await fetchJson('/api/upload', {
      method: 'POST',
      body: formData,
    });
    uploaded.push(payload.image_id);
  }

  uploadIds.value = uploaded;
  return uploaded;
}

async function ensureCopySet() {
  const payload = await fetchJson('/api/copy', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ keyword: keyword.value.trim() }),
  });

  copySets.value = (payload.sets || []).map((item) => ({
    ...item,
    lines_cn: Array.isArray(item.lines_cn) ? item.lines_cn.slice(0, 3) : [],
    lines_en: Array.isArray(item.lines_en) ? item.lines_en.slice(0, 3) : [],
  }));

  const recommended = copySets.value.find((item) => item.recommend) || copySets.value[0];
  if (recommended) {
    setSelectedCopy(recommended);
  }
  return copySets.value;
}

async function composeCurrentSet() {
  if (!uploadIds.value.length) {
    throw new Error('请先上传并分析图片。');
  }

  const payload = await fetchJson('/api/compose', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_ids: uploadIds.value,
      copy_set_id: Number(selectedCopyId.value || 1),
      keyword: keyword.value.trim(),
      use_analyze_crop: true,
      text_shadow: true,
      film_grain: false,
    }),
  });

  resultUrl.value = `${API_BASE}${payload.result_url}`;
  report.value = `已生成拼图，job_id：${payload.job_id}`;
  return payload;
}

async function generatePuzzle() {
  if (!keyword.value.trim()) {
    report.value = '错误：关键词不能为空。';
    return;
  }

  if (images.value.some((image) => !image)) {
    report.value = '错误：请先上传 3 张素材图。';
    return;
  }

  isBusy.value = true;
  report.value = '正在上传图片并生成拼图...';

  try {
    const uploadedIds = await uploadAllImages();
    const analysisPayload = await fetchJson('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ image_ids: uploadedIds }),
    });
    uploadIds.value = analysisPayload.ordered_ids || uploadedIds;

    await ensureCopySet();
    await composeCurrentSet();
  } catch (error) {
    report.value = `生成失败：${error.message}`;
  } finally {
    isBusy.value = false;
  }
}

async function loadDefaultMaterials() {
  try {
    const loaded = await Promise.all(
      DEFAULT_MATERIAL_FILES.map(async (filename, index) => {
        const response = await fetch(`${API_BASE}/uploads/${filename}`);
        if (!response.ok) {
          throw new Error(`无法加载默认素材 ${filename}`);
        }
        const blob = await response.blob();
        return new File([blob], filename, { type: blob.type || 'image/jpeg' });
      }),
    );

    images.value = loaded;
    resetCropDrafts();
    resetImageTransforms();
    report.value = '已加载默认素材图。';
  } catch (error) {
    report.value = `默认素材加载失败：${error.message}`;
    images.value = [null, null, null];
  }
}

onMounted(async () => {
  await loadDefaultMaterials();
});

async function generateCopySets() {
  if (!keyword.value.trim()) {
    report.value = '错误：关键词不能为空。';
    return;
  }

  try {
    await ensureCopySet();
    report.value = '已生成 3 套文案方案，可在文案生成区选择。';
  } catch (error) {
    report.value = `文案生成失败：${error.message}`;
  }
}

onBeforeUnmount(() => {
  for (const url of objectUrlCache.values()) {
    URL.revokeObjectURL(url);
  }
  objectUrlCache.clear();
});

function fillDemo() {
  keyword.value = '禾木';
  images.value = [null, null, null];
  report.value = '已填充示例关键词，上传 3 张图片后再点击“生成拼图”。';
  resultUrl.value = '';
  copySets.value = [];
  selectedCopyId.value = 1;
  selectedCopy.value = {
    id: 1,
    recommend: true,
    lines_cn: ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
    lines_en: ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
  };
  customCopyText.value = selectedCopy.value.lines_cn.join('\n');
  resetCropDrafts();
  resetImageTransforms();
}

function syncSelectedCopyFromCustom() {
  const lines = customCopyText.value
    .split(/\n/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 3);

  if (!lines.length) {
    return;
  }

  selectedCopyId.value = 'custom';
  selectedCopy.value = {
    id: 'custom',
    recommend: false,
    lines_cn: lines,
    lines_en: lines.map((line) => `A cinematic reflection on “${line.replace(/[，。！？；：、]/g, '')}”.`),
  };
}

function updateCopyFromSelection() {
  const found = copySets.value.find((item) => item.id === selectedCopyId.value);
  if (found) {
    selectedCopy.value = {
      ...found,
      lines_cn: [...(found.lines_cn || [])],
      lines_en: [...(found.lines_en || [])],
    };
    customCopyText.value = (selectedCopy.value.lines_cn || []).slice(0, 3).join('\n');
  }
}

function previewCopyOnCanvas() {
  const lines = (selectedCopy.value.lines_cn || []).slice(0, 3);
  if (!lines.length) {
    report.value = '请先生成或填写文案后再预览。';
    return;
  }

  customCopyText.value = lines.join('\n');
  previewOverlayVisible.value = true;
  report.value = '已将当前文案叠加到预览图中。';
}

function getPreviewCopyForSlot(index) {
  return {
    cn: selectedCopy.value.lines_cn?.[index] || '',
    en: selectedCopy.value.lines_en?.[index] || '',
  };
}

async function downloadResult() {
  if (!resultUrl.value) {
    report.value = '请先生成拼图后再下载。';
    return;
  }

  try {
    const response = await fetch(resultUrl.value, { method: 'GET' });
    if (!response.ok) {
      throw new Error('无法获取生成结果');
    }

    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'triptych-result.jpg';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
    report.value = '导出成功：拼图已下载到本地。';
  } catch (error) {
    const a = document.createElement('a');
    a.href = resultUrl.value;
    a.download = 'triptych-result.jpg';
    document.body.appendChild(a);
    a.click();
    a.remove();
    report.value = `导出失败：${error.message}`;
  }
}
</script>

<template>
<div class="min-h-screen bg-[#f4f4f4] text-[#333333]">
<div class="mx-auto flex min-h-screen max-w-md flex-col bg-white shadow-[0_0_0_1px_rgba(0,0,0,0.04)]">
  <header class="flex items-center justify-between border-b border-[#eaeaea] bg-white px-4 py-3">
    <button type="button" class="flex h-8 w-8 items-center justify-center rounded-full bg-transparent text-[#333333]">
      <svg viewBox="0 0 24 24" class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M15 18l-6-6 6-6" />
      </svg>
    </button>

    <div class="text-sm font-medium tracking-[0.08em] text-[#333333]">拼图编辑</div>

    <button
      type="button"
      class="inline-flex items-center gap-1.5 rounded-full border border-[#1f1f1f] bg-[#111111] px-2.5 py-1 text-[10px] font-medium tracking-[0.08em] text-white shadow-[0_4px_10px_rgba(17,17,17,0.18)] transition hover:bg-[#1b1b1b] active:scale-[0.98]"
      @click="downloadResult"
    >
      <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 3v12" />
        <path d="M7 20l5 5 5-5" />
        <path d="M5 21h14" />
      </svg>
      <span>导出</span>
    </button>
  </header>

  <main class="flex-1 bg-[#f7f7f7] pb-28">
    <div class="px-0 pt-0">
      <div class="rounded-none bg-[#f3f3f3] p-0 shadow-none">
        <div class="mx-auto flex h-[65vh] w-full max-w-none flex-col overflow-hidden border border-[#ececec] bg-white shadow-[0_10px_24px_rgba(0,0,0,0.04)]">
          <div
            v-for="(image, index) in images"
            :key="index"
            class="relative flex-1 overflow-hidden bg-black"
            :class="selectedSegment === index ? 'ring-2 ring-[#FF007F] ring-offset-1 ring-offset-white' : ''"
            draggable="true"
            @dragstart="onSlotDragStart(index)"
            @dragover.prevent
            @drop="onSlotDrop(index)"
          >
            <img
              v-if="image"
              :src="getObjectUrl(image)"
              alt="素材层"
              class="pointer-events-auto h-full w-full cursor-move object-contain select-none bg-white"
              :style="getImageTransformStyle(index)"
              :data-index="index"
              @pointerdown="startImageTransform(index, $event)"
              @pointermove="moveImageTransform($event)"
              @pointerup="stopImageTransform($event)"
              @pointercancel="stopImageTransform($event)"
              @pointerleave="stopImageTransform($event)"
              @wheel.prevent="onImageWheel(index, $event)"
              @click="selectSegment(index)"
            />
            <div v-else class="flex h-full items-center justify-center text-[10px] font-medium tracking-[0.08em] text-[#999999]" @click="selectSegment(index)">
              素材 {{ index + 1 }}
            </div>

            <div v-if="previewOverlayVisible" class="pointer-events-none absolute inset-x-0 bottom-0 z-10 flex h-[40%] flex-col items-center justify-end pb-1 text-center text-white">
              <div class="mb-0.1 text-[11px] font-light tracking-[0.06em] text-white drop-shadow-[0_2px_6px_rgba(0,0,0,0.75)]">
                {{ getPreviewCopyForSlot(index).cn || '' }}
              </div>
              <div class="text-[9px] font-light tracking-[0.08em] text-white/70 drop-shadow-[0_2px_6px_rgba(0,0,0,0.7)]">
                {{ getPreviewCopyForSlot(index).en || '' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-3 bg-white px-3 pb-3 pt-2">
      <div class="mb-1.5 flex items-center justify-between">
        <span class="text-[10px] font-medium tracking-[0.1em] text-[#999999] uppercase">文案</span>
        <div class="flex items-center gap-2">
          <button type="button" class="rounded-full border border-[#e9e9e9] px-2 py-0.5 text-[10px] font-medium text-[#333333]" @click="generateCopySets">
            生成
          </button>
          <button type="button" class="rounded-full border border-[#FF007F] bg-[#fff1f8] px-2 py-0.5 text-[10px] font-medium text-[#FF007F]" @click="previewCopyOnCanvas">
            预览
          </button>
        </div>
      </div>

      <div class="relative">
        <textarea
          v-model="customCopyText"
          rows="2"
          class="w-full resize-none rounded-xl border border-[#e9e9e9] bg-white px-2.5 pb-8 pt-2.5 pr-10 text-[12px] leading-5 text-[#333333] placeholder:text-[#999999] focus:border-[#FF007F] focus:outline-none"
          placeholder="输入关键词生成文案，或直接粘贴..."
          @input="syncSelectedCopyFromCustom"
        />
        <button type="button" class="absolute right-2.5 top-2.5 flex h-7 w-7 items-center justify-center rounded-full bg-[#f7f7f7] text-[#666666] transition hover:bg-[#ededed]" @click="copyCurrentText">
          <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V5a2 2 0 0 1 2-2h10" />
          </svg>
        </button>
      </div>

      <div v-if="copySets.length" class="mt-2 space-y-1.5">
        <button
          v-for="item in copySets"
          :key="item.id"
          type="button"
          class="w-full rounded-2xl border px-3 py-2 text-left transition"
          :class="selectedCopyId === item.id ? 'border-[#FF007F] bg-[#fff1f8] text-[#333333]' : 'border-[#ededed] bg-[#fafafa] text-[#333333]'"
          @click="() => { setSelectedCopy(item); updateCopyFromSelection(); }"
        >
          <div class="mb-1 flex items-center justify-between text-[10px] text-[#999999]">
            <span>{{ item.recommend ? '推荐' : '备选' }}</span>
            <span>方案 {{ item.id }}</span>
          </div>
          <div class="space-y-1 text-[12px] leading-5">
            <div v-for="(line, index) in (item.lines_cn || []).slice(0, 3)" :key="index">{{ line }}</div>
          </div>
        </button>
      </div>
    </div>
  </main>

  <div v-if="bottomSheetOpen" class="fixed inset-x-0 bottom-0 mx-auto max-w-md border-t border-[#ededed] bg-white px-3 pb-[calc(env(safe-area-inset-bottom)+8px)] pt-2 shadow-[0_-10px_18px_rgba(0,0,0,0.07)]">
    <div class="mb-1.5 flex justify-end">
      <button type="button" class="flex h-6 w-6 items-center justify-center rounded-full bg-[#f5f5f5] text-[#666666]" @click="toggleBottomSheet">
        <svg viewBox="0 0 24 24" class="h-3.5 w-3.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
    </div>

    <div class="flex items-center">
      <button
        type="button"
        class="flex w-[64px] flex-col items-center justify-center gap-1 rounded-xl border border-[#efefef] bg-white p-1.5 text-[#333333] transition"
        :class="replacePulse ? 'animate-pulse border-[#FF007F] text-[#FF007F]' : ''"
        @click="handleReplace"
      >
        <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <rect x="4" y="5" width="10" height="10" rx="2" />
          <rect x="10" y="9" width="10" height="10" rx="2" />
        </svg>
        <span class="text-[9px] font-medium">替换</span>
      </button>
    </div>
  </div>

  <button
    v-else
    type="button"
    class="fixed bottom-3 right-3 flex h-9 w-9 items-center justify-center rounded-full border border-[#efefef] bg-white text-[#666666] shadow-[0_6px_16px_rgba(0,0,0,0.08)]"
    @click.stop="toggleBottomSheet"
  >
    <svg viewBox="0 0 24 24" class="h-4 w-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M6 9l6 6 6-6" />
    </svg>
  </button>
</div>

<input id="replace-upload" ref="replaceInput" type="file" accept="image/*" class="hidden" @change="onFilePicked" />
</div>
</template>
