import {makeProject} from '@motion-canvas/core';

import shadow from './scenes/shadow?scene';
import lines from './scenes/lines?scene';

export default makeProject({
  scenes: [shadow, lines],
});
