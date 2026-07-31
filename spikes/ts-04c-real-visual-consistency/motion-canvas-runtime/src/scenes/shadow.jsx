import {Line, Rect, Txt, makeScene2D} from '@motion-canvas/2d';
import {createRef, createSignal} from '@motion-canvas/core';
import fixture from '../../../fixtures/hybrid-preview-scenes.json';
import {compileHybridScene, evaluateHybridFrame} from '../../../src/hybrid-scene-compiler.js';

const compiled = compileHybridScene(fixture.scenes.find(scene => scene.id === 'shadow-preview'));

export default makeScene2D(function* (view) {
  const flashlight = createRef();
  const shadow = createRef();
  const rays = createRef();
  const progress = createSignal(0);
  const shadowScene = compiled.nodes;
  const lamp = shadowScene.find(node => node.id === 'flashlight');
  const shadowNode = shadowScene.find(node => node.id === 'shadow');

  view.add(
    <>
      <Txt text="手电筒靠近，影子为什么变大？" y={-420} fontSize={34} fill="#1f2933" />
      <Line ref={rays} points={() => {
        const frame = evaluateHybridFrame(compiled, progress());
        return frame.connectors.flatMap(connector => [
          [connector.from.x - 500, connector.from.y - 500],
          [connector.to.x - 500, connector.to.y - 500],
        ]);
      }} stroke="#ef8a80" lineWidth={6} />
      <Rect ref={flashlight} x={lamp.x - 500} y={lamp.y - 500} width={lamp.width} height={lamp.height} radius={10} fill="#f6d365" stroke="#1f2933" lineWidth={4} />
      <Txt text="手电筒" x={lamp.x - 500} y={lamp.y - 500} fontSize={20} fill="#1f2933" />
      <Rect x={shadowScene.find(node => node.id === 'toy').x - 500} y={-0} width={76} height={150} radius={10} fill="#66b67d" stroke="#1f2933" lineWidth={4} />
      <Txt text="玩偶" x={-40} y={0} fontSize={20} fill="#1f2933" />
      <Rect ref={shadow} x={shadowNode.x - 500} y={shadowNode.y - 500} width={shadowNode.width} height={shadowNode.height} radius={10} fill="#202b36" />
      <Rect x={360} y={0} width={24} height={330} fill="#9aa4ad" />
      <Txt text="墙" x={360} y={-190} fontSize={20} fill="#1f2933" />
    </>,
  );

  yield* progress(1, 1.8);
});
