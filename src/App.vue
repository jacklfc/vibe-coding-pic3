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
const report = ref('');
const isBusy = ref(false);
const uploadIds = ref([]);
const copySets = ref([]);
const selectedCopyId = ref(1);
const resultUrl = ref('');
const selectedCopy = ref({
  id: 1,
  lines_cn: [
    ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
    ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
    ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
  ],
  lines_en: [
    ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
    ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
    ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
  ],
});

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
  const incoming = Array.from(event.target.files || []).filter((file) => file && file.type.startsWith('image/')).slice(0, 3);
  if (!incoming.length) {
    report.value = '错误：请上传合法的图片文件。';
    return;
  }

  images.value = [incoming[0] || null, incoming[1] || null, incoming[2] || null];
  resetCropDrafts();
  report.value = '';
  event.target.value = '';
}

function setSelectedCopy(item) {
  selectedCopyId.value = item.id;
  selectedCopy.value = item;
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
    lines_cn: normalizeSentenceMatrix(item.lines_cn),
    lines_en: normalizeSentenceMatrix(item.lines_en),
  }));
  const recommended = copySets.value.find((item) => item.recommend) || copySets.value[0];
  selectedCopyId.value = recommended?.id || 1;
  selectedCopy.value = recommended || selectedCopy.value;
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
    report.value = '已加载默认素材图。';
  } catch (error) {
    report.value = `默认素材加载失败：${error.message}`;
    images.value = [null, null, null];
  }
}

onMounted(() => {
  loadDefaultMaterials();
});

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
  selectedCopy.value = {
    id: 1,
    lines_cn: [
      ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
      ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
      ['山谷里，雾气先学会沉默', '风沿着谷地把时间慢慢铺开', '人最终回到根下，才听见自己'],
    ],
    lines_en: [
      ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
      ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
      ['In the valley, the mist learns silence before dawn.', 'Wind follows the valley and lets time unfold gradually.', 'Only returning to the roots do we hear ourselves clearly.'],
    ],
  };
  resetCropDrafts();
}

function normalizeSentenceMatrix(value) {
  const matrix = Array.from({ length: 3 }, () => Array.from({ length: 3 }, () => ''));
  if (!Array.isArray(value)) return matrix;

  if (Array.isArray(value[0])) {
    value.slice(0, 3).forEach((segment, segmentIndex) => {
      if (!Array.isArray(segment)) return;
      segment.slice(0, 3).forEach((line, lineIndex) => {
        matrix[segmentIndex][lineIndex] = String(line ?? '');
      });
    });
    return matrix;
  }

  value.slice(0, 9).forEach((line, index) => {
    const segmentIndex = Math.floor(index / 3);
    const lineIndex = index % 3;
    if (segmentIndex < 3 && lineIndex < 3) {
      matrix[segmentIndex][lineIndex] = String(line ?? '');
    }
  });

  return matrix;
}

function autoEnglishFromChinese(text) {
  const clean = (text || '').replace(/[，。！？；：、]/g, '').trim();
  if (!clean) return '';
  if (clean.length <= 8) {
    return `A quiet note on ${clean}.`;
  }
  return `A cinematic reflection on “${clean}”.`;
}

function getSentence(type, segmentIndex, lineIndex) {
  const collection = selectedCopy.value?.[type === 'cn' ? 'lines_cn' : 'lines_en'];
  return collection?.[segmentIndex]?.[lineIndex] ?? '';
}

function setSentence(type, segmentIndex, lineIndex, value) {
  if (!selectedCopy.value) return;
  const collection = selectedCopy.value[type === 'cn' ? 'lines_cn' : 'lines_en'];
  if (!collection?.[segmentIndex]) return;
  collection[segmentIndex][lineIndex] = value;
}

function onChineseLineInput(segmentIndex, lineIndex, value) {
  setSentence('cn', segmentIndex, lineIndex, value);
  setSentence('en', segmentIndex, lineIndex, autoEnglishFromChinese(value));
}

function previewText(lineIndex) {
  if (!selectedCopy.value?.lines_cn?.[lineIndex]) return '';
  return selectedCopy.value.lines_cn[lineIndex][0] || '';
}

function previewTextEn(lineIndex) {
  if (!selectedCopy.value?.lines_en?.[lineIndex]) return '';
  return selectedCopy.value.lines_en[lineIndex][0] || '';
}

function updateCopyFromSelection() {
  const found = copySets.value.find((item) => item.id === selectedCopyId.value);
  if (found) {
    selectedCopy.value = found;
  }
}

function downloadResult() {
  if (!resultUrl.value) {
    report.value = '请先生成拼图后再下载。';
    return;
  }

  const a = document.createElement('a');
  a.href = resultUrl.value;
  a.download = 'triptych-result.jpg';
  a.click();
}
</script>

<template>
  <div class="min-h-screen bg-slate-950 px-6 py-8 text-slate-50">
    <div class="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[420px_1fr]">
      <section class="rounded-2xl border border-slate-700/80 bg-slate-900/90 p-5 shadow-2xl shadow-slate-950/30">
        <h1 class="mb-5 text-2xl font-semibold tracking-wide text-slate-100">文案块</h1>

        <div class="mb-5 space-y-2">
          <label for="keyword" class="block text-sm text-slate-300">关键词</label>
          <input
            id="keyword"
            v-model="keyword"
            type="text"
            class="w-full rounded-xl border border-slate-700 bg-slate-950/80 px-3 py-2.5 text-base text-slate-50 outline-none ring-0 placeholder:text-slate-500 focus:border-sky-500"
            placeholder="例如：禾木"
          />
        </div>

        <div class="mb-6 rounded-2xl border border-slate-700 bg-slate-950/60 p-3">
          <label class="mb-3 block text-sm text-slate-300">文案修改（每段 3 句，中文 + 英文分开编辑）</label>
          <div class="space-y-3">
            <div v-for="segmentIndex in 3" :key="segmentIndex" class="rounded-xl border border-slate-700 bg-slate-900/80 p-2">
              <div class="mb-2 text-[11px] text-slate-400">第 {{ segmentIndex }} 段</div>
              <div class="space-y-2">
                <div v-for="lineIndex in 3" :key="lineIndex" class="space-y-1.5">
                  <input
                    :value="getSentence('cn', segmentIndex - 1, lineIndex - 1)"
                    @input="onChineseLineInput(segmentIndex - 1, lineIndex - 1, $event.target.value)"
                    class="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-50 outline-none focus:border-sky-500"
                  />
                  <input
                    :value="getSentence('en', segmentIndex - 1, lineIndex - 1)"
                    @input="setSentence('en', segmentIndex - 1, lineIndex - 1, $event.target.value)"
                    class="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-50 outline-none focus:border-sky-500"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex flex-wrap gap-3">
          <button
            :disabled="isBusy"
            class="rounded-xl bg-sky-400 px-4 py-2.5 font-medium text-slate-950 shadow-lg shadow-sky-500/20 transition hover:bg-sky-300 disabled:cursor-not-allowed disabled:opacity-60"
            @click="generatePuzzle"
          >
            {{ isBusy ? '生成中...' : '生成拼图' }}
          </button>
          <button
            class="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-slate-100 transition hover:bg-slate-700"
            @click="fillDemo"
          >
            加载示例
          </button>
          <button
            v-if="resultUrl"
            class="rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-slate-100 transition hover:bg-slate-700"
            @click="downloadResult"
          >
            下载 JPG
          </button>
        </div>

        <p v-if="report" class="mt-4 whitespace-pre-line rounded-xl border border-slate-700 bg-slate-950/70 p-3 text-sm leading-7 text-slate-200">
          {{ report }}
        </p>
      </section>

      <section class="rounded-2xl border border-slate-700/80 bg-slate-900/90 p-5 shadow-2xl shadow-slate-950/30">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-2xl font-semibold tracking-wide text-slate-100">最终输出预览</h2>
          <span class="text-xs text-slate-400">后端：{{ API_BASE }}</span>
        </div>

        <div class="mb-5 rounded-xl border border-slate-700 bg-slate-950/60 p-3">
          <label class="mb-2 block text-sm text-slate-300">上传 3 张素材图</label>
          <input
            type="file"
            accept="image/*"
            multiple
            class="block w-full text-sm text-slate-300 file:mr-3 file:rounded-lg file:border-0 file:bg-sky-500 file:px-3 file:py-2 file:text-sm file:font-medium file:text-slate-950"
            @change="onFilePicked"
          />
        </div>

        <div class="final-collage relative mx-auto aspect-[3/4] w-full max-w-[560px] overflow-hidden rounded-2xl border border-slate-700 bg-slate-950/70 p-2">
          <div v-for="(image, index) in images" :key="index" class="segment-slot relative h-[33.333%] overflow-hidden rounded-lg border border-slate-700 bg-slate-900">
            <img
              v-if="image"
              :src="getObjectUrl(image)"
              class="absolute inset-0 h-full w-full object-cover"
              alt="素材层"
            />
            <div v-else class="flex h-full items-center justify-center text-[11px] text-slate-500">素材 {{ index + 1 }}</div>

            <div
              v-if="image"
              class="crop-frame absolute border-2 border-sky-400 bg-sky-400/10 shadow-[0_0_0_9999px_rgba(2,6,23,0.45)]"
              :style="cropStyleFor(index)"
              @pointerdown="startCropDrag(index, $event)"
              @pointermove="onCropDrag"
              @pointerup="stopCropDrag"
              @pointerleave="stopCropDrag"
              @wheel.prevent="onWheelZoom(index, $event)"
            >
              <div class="absolute inset-0 border border-dashed border-sky-300/80" />
            </div>
          </div>

          <div v-if="selectedCopy.lines_cn.length" class="pointer-events-none absolute inset-0 z-10">
            <div
              v-for="(segment, segmentIndex) in selectedCopy.lines_cn"
              :key="segmentIndex"
              class="absolute left-1/2 w-[78%] -translate-x-1/2 text-center text-slate-50"
              :style="{ top: `${segmentIndex * 33.333 + 10}%` }"
            >
              <div v-for="(line, lineIndex) in segment" :key="lineIndex" class="mb-2">
                <div class="text-[14px] font-light leading-[1.2] tracking-[0.04em] text-white/95">{{ line }}</div>
                <div class="mt-1 text-[10px] font-light tracking-[0.12em] text-white/80">{{ selectedCopy.lines_en?.[segmentIndex]?.[lineIndex] || '' }}</div>
              </div>
            </div>
          </div>
        </div>

        <div class="mt-4 text-[11px] text-slate-400">拖拽移动 · 滚轮缩放 · 2.25:1 比例锁定</div>

        <div class="mt-5 rounded-2xl border border-slate-700 bg-slate-950/60 p-4">
          <div class="mb-3 flex items-center justify-between">
            <span class="text-sm text-slate-300">最终输出结果</span>
            <button
              v-if="resultUrl"
              class="rounded-xl border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-100 hover:bg-slate-700"
              @click="downloadResult"
            >
              下载结果
            </button>
          </div>

          <div class="flex min-h-[180px] items-center justify-center rounded-2xl border border-slate-700 bg-slate-950/70 p-3">
            <img
              v-if="resultUrl"
              :src="resultUrl"
              alt="Triptych result"
              class="max-h-[260px] w-full max-w-[240px] rounded-xl border border-slate-700 object-contain"
            />
            <div v-else class="text-sm text-slate-500">生成结果会在这里显示</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>
