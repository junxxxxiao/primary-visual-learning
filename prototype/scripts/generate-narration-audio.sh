#!/bin/zsh
set -euo pipefail

script_dir=${0:A:h}
audio_dir=${script_dir:h}/assets/audio
voice='Shelley (中文（中国大陆）)'

generate_narration() {
  local name=$1
  local rate=$2
  local copy=$3
  local source_file="/tmp/sound-demo-${name}.aiff"
  say -v "$voice" -r "$rate" -o "$source_file" "$copy"
  afconvert -f WAVE -d LEI16@44100 "$source_file" "$audio_dir/narration-${name}.wav"
}

generate_narration lesson-intro 164 '现在，我们正式来解决这个问题：更用力拨同一根弦，音调会更高吗？我会先用三小段画面，一步一步讲清楚。讲解时只需要看和听，等讲完了，再轮到你亲手拨琴弦验证。'
generate_narration main-1 164 '先想象一下，你手里就是同一把吉他。我们只把手指的力气变大，琴弦还是那一根，长度、松紧、粗细都不动。这样比较才公平，对吧？现在，我们要同时留意三件事：它摆得多开，振得多快，还有听起来怎样。'
generate_narration main-2 164 '来，看这里。轻轻拨，琴弦只在中间附近摆动；用力拨，它一下子摆得更开了。可是你再看仔细一点：同样一小段时间里，两根弦来回的次数，差不多。原来，摆得更开，不等于来回得更快。'
generate_narration main-3 162 '现在给刚才的发现起个名字。琴弦摆动的范围，叫振幅；单位时间里振动的次数，叫频率。力气变大，主要让振幅变大，所以声音更响；频率基本不变，所以音调也基本不变。注意，是在同一根弦、其他条件不变的时候哦。'
generate_narration practice 166 '讲到这里，轮到你了！现在你可以动手来试试。先轻轻拨一次，再用力拨一次，看看刚才的发现是不是真的。'
generate_narration vacuum-1 164 '如果没有空气呢？问得好！先别急着回答听不听得到。我们把它拆成两步：第一步，琴弦自己还会不会振动；第二步，这个振动还能不能走到耳朵。'
generate_narration vacuum-2 164 '平时，琴弦不会直接碰到你的耳朵。它先推动旁边的空气，空气再像接力队一样，把振动一层一层传过来。最后，耳朵接到了这个振动，我们才听见声音。'
generate_narration vacuum-3 162 '现在把空气拿走。琴弦呢？它还是会振动。可是中间没有空气接力，振动就传不到远处的耳朵。所以，没有空气时，琴弦仍然在动，我们却听不到通过空气传来的声音。'
generate_narration return-main 164 '这个问题我们弄明白了。如果你也明白了，让我们再回到刚才的琴弦振动，从被打断的那一小段重新看起吧。'

echo "Narration fixtures written to $audio_dir"
