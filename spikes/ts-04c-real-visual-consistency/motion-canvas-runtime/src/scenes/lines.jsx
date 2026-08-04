import {Line, Txt, makeScene2D} from '@motion-canvas/2d';
import {createRef} from '@motion-canvas/core';
import fixture from '../../../fixtures/hybrid-preview-scenes.json';
import {compileHybridScene} from '../../../src/hybrid-scene-compiler.js';

const compiled = compileHybridScene(fixture.scenes.find(scene => scene.id === 'line-preview'));
const first = compiled.function_lines[0];
const second = compiled.function_lines[1];
const scale = 48;
const origin = {x: -180, y: 180};
const point = ({x, y}) => [origin.x + x * scale, origin.y - y * scale];

export default makeScene2D(function* (view) {
  const firstLine = createRef();
  const secondLine = createRef();
  const intersection = compiled.derived.first_intersection;
  view.add(
    <>
      <Txt text="两条直线为什么只在一个点相交？" y={-420} fontSize={34} fill="#1f2933" />
      <Line points={[[origin.x - 180, origin.y], [origin.x + 300, origin.y]]} endArrow stroke="#1f2933" lineWidth={4} />
      <Line points={[[origin.x, origin.y + 180], [origin.x, origin.y - 300]]} endArrow stroke="#1f2933" lineWidth={4} />
      <Txt text="x" x={origin.x + 320} y={origin.y + 18} fontSize={24} fill="#1f2933" />
      <Txt text="y" x={origin.x - 18} y={origin.y - 320} fontSize={24} fill="#1f2933" />
      <Line ref={firstLine} points={first.points.map(point)} stroke="#4f86f7" lineWidth={7} />
      <Line ref={secondLine} points={second.points.map(point)} stroke="#7c8793" lineWidth={7} />
      <Txt text={first.label} x={origin.x + 150} y={origin.y - 180} fontSize={22} fill="#4f86f7" />
      <Txt text={second.label} x={origin.x + 130} y={origin.y - 250} fontSize={22} fill="#7c8793" />
      <Txt text={`交点 (${intersection.x},${intersection.y})`} x={origin.x + intersection.x * scale + 70} y={origin.y - intersection.y * scale - 30} fontSize={22} fill="#1f2933" />
    </>,
  );
  yield* firstLine().opacity(1, 0.4);
  yield* secondLine().opacity(1, 0.4);
});
