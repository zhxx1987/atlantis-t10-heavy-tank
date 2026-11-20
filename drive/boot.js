import { Viewer } from '/AtlantisGallery/atlantis-renderer/frontend/webgpu/viewer.js';

// Preserve individual wheel and track nodes in the immutable preview GLB.
// The downloadable Atlantis driving host sets the same two flags.
function articulatableGlb(buffer) {
  const bytes = new Uint8Array(buffer);
  const jsonLength = new DataView(buffer).getUint32(12, true);
  const doc = JSON.parse(new TextDecoder().decode(bytes.subarray(20, 20 + jsonLength)));
  for (const node of doc.nodes) {
    if (node.mesh === undefined) continue;
    node.extras = {...node.extras, aps_no_instancing: true, aps_no_batch: true};
  }
  const json = new TextEncoder().encode(JSON.stringify(doc));
  const paddedLength = Math.ceil(json.length / 4) * 4;
  const result = new Uint8Array(buffer.byteLength - jsonLength + paddedLength);
  result.set(bytes.subarray(0, 20));
  const header = new DataView(result.buffer);
  header.setUint32(8, result.byteLength, true);
  header.setUint32(12, paddedLength, true);
  result.fill(32, 20, 20 + paddedLength);
  result.set(json, 20);
  result.set(bytes.subarray(20 + jsonLength), 20 + paddedLength);
  return result.buffer;
}

try {
  const viewer = new Viewer(document.querySelector('#stage'), undefined, {
    presentation: true,
    singleShadow: true,
    shadowMapSize: 2048,
    shadowCasterBatching: false,
    async readGalleryMesh(url, signal) {
      const response = await fetch(url, {signal});
      if (!response.ok) throw Error('Model request failed (' + response.status + ')');
      const raw = await response.arrayBuffer();
      return {buffer: new URL(url).pathname.endsWith('/T10.glb') ? articulatableGlb(raw) : raw,
              metadata: {adapter: 'gallery-drive'}};
    },
  });
  window.sceneViewer = {viewer, loaded: false};
  await viewer.ready;
  await viewer.loadScene(new URL('./scene.json?v=20261120-suspension-v4', import.meta.url).href);
  window.sceneViewer.loaded = true;
} catch (error) {
  document.querySelector('#error').textContent = 'Driving scene could not start. ' + error.message;
  console.error(error);
}
