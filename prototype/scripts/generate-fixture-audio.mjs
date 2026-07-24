import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const outputDirectory = resolve(scriptDirectory, '../assets/audio');
const sampleRate = 44100;

mkdirSync(outputDirectory, { recursive: true });

function tone(frequency, duration, amplitude) {
  const frames = Math.round(sampleRate * duration);
  return Array.from({ length: frames }, (_, index) => {
    const time = index / sampleRate;
    const envelope = Math.min(1, time / 0.015) * Math.exp(-2.8 * time / duration);
    return Math.sin(2 * Math.PI * frequency * time) * amplitude * envelope;
  });
}

function silence(duration) {
  return Array(Math.round(sampleRate * duration)).fill(0);
}

function writeWav(filename, samples) {
  const dataBytes = samples.length * 2;
  const buffer = Buffer.alloc(44 + dataBytes);
  buffer.write('RIFF', 0);
  buffer.writeUInt32LE(36 + dataBytes, 4);
  buffer.write('WAVE', 8);
  buffer.write('fmt ', 12);
  buffer.writeUInt32LE(16, 16);
  buffer.writeUInt16LE(1, 20);
  buffer.writeUInt16LE(1, 22);
  buffer.writeUInt32LE(sampleRate, 24);
  buffer.writeUInt32LE(sampleRate * 2, 28);
  buffer.writeUInt16LE(2, 32);
  buffer.writeUInt16LE(16, 34);
  buffer.write('data', 36);
  buffer.writeUInt32LE(dataBytes, 40);
  samples.forEach((sample, index) => {
    buffer.writeInt16LE(Math.round(Math.max(-1, Math.min(1, sample)) * 32767), 44 + index * 2);
  });
  writeFileSync(resolve(outputDirectory, filename), buffer);
}

writeWav('calibration-loudness.wav', [
  ...tone(440, 0.82, 0.08), ...silence(0.45), ...tone(440, 0.82, 0.85)
]);
writeWav('calibration-pitch.wav', [
  ...tone(330, 0.72, 0.5), ...silence(0.5), ...tone(523.25, 0.72, 0.5)
]);
writeWav('string-light.wav', tone(440, 1.1, 0.24));
writeWav('string-strong.wav', tone(440, 1.1, 0.72));

console.log(`Generated fixed audio fixtures in ${outputDirectory}`);
