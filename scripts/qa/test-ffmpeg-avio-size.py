#!/usr/bin/env python3
"""Exercise both production FFmpegFile copies against real host FFmpeg.

Catches a missing AVIO size callback that makes valid Xing MP3s look
concatenated. Engine File is a memory-backed test adapter; codecs/demuxing and
FFmpegFile are real. This does not validate Android performance or game assets.
Requires ffmpeg, C++17 and libavformat/libavcodec/libavutil development headers.
GX_FFMPEG_INCLUDE_DIR may point to headers extracted without installing them.
"""
import ctypes.util
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

TYPES = r'''
#pragma once
#include <cassert>
#include <cstdint>
using Bool = bool;
using Int = int;
using Int64 = int64_t;
using UnsignedInt = unsigned int;
using UnsignedByte = unsigned char;
#define LOGGING_LEVEL 0
#define LOGLEVEL_NONE 0
#define DEBUG_LOG(args) ((void)0)
#define DEBUG_ASSERTCRASH(condition, args) assert(condition)
#define GX_AUDIO_TRACE(...) ((void)0)
'''

FILE_ADAPTER = r'''
#pragma once
#include <algorithm>
#include <cassert>
#include <cstring>
#include <utility>
#include <vector>
// Only the File contract used by production FFmpegFile. close() owns the handle.
struct File {
    std::vector<uint8_t> bytes;
    size_t offset = 0;
    explicit File(std::vector<uint8_t> value) : bytes(std::move(value)) {}
    int read(void *dst, int count) {
        const size_t n = std::min(size_t(count), bytes.size() - offset);
        std::memcpy(dst, bytes.data() + offset, n);
        offset += n;
        return int(n);
    }
    int size() { return int(bytes.size()); }
    void close() { delete this; }
};
'''

HARNESS = r'''
#include "VideoDevice/FFmpeg/FFmpegFile.h"
#include "Common/file.h"
extern "C" {
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
}
#include <cstdarg>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <string>

static int invalidConcatenated = 0;
static void capture(void *, int level, const char *format, va_list args) {
    if (level > av_log_get_level()) return;
    char line[4096];
    std::vsnprintf(line, sizeof(line), format, args);
    if (std::string(line).find("invalid concatenated") != std::string::npos)
        ++invalidConcatenated;
}
static int decode(const std::vector<uint8_t>& bytes) {
    FFmpegFile file;
    if (!file.open(new File(bytes))) return -1;
    int samples = 0;
    file.setFrameCallback([&](AVFrame *frame, int, int type, void *) {
        if (type == AVMEDIA_TYPE_AUDIO) samples += frame->nb_samples;
    });
    for (int packet = 0; packet < 10000 && !file.isAtEof(); ++packet)
        file.decodePacket();
    assert(file.isAtEof());
    return samples;
}
int main(int argc, char **argv) {
    assert(argc == 2);
    std::ifstream input(argv[1], std::ios::binary);
    std::vector<uint8_t> valid((std::istreambuf_iterator<char>(input)), {});
    av_log_set_level(AV_LOG_WARNING);
    av_log_set_callback(capture);
    const int samples = decode(valid);
    if (invalidConcatenated != 0 || samples <= 0) {
        std::fprintf(stderr, "FAIL: valid Xing MP3 produced %d invalid-concatenation warnings (%d samples)\n",
                     invalidConcatenated, samples);
        return 1;
    }
    // A genuinely concatenated file must still diagnose its inconsistent header.
    std::vector<uint8_t> concatenated = valid;
    concatenated.insert(concatenated.end(), valid.begin(), valid.end());
    invalidConcatenated = 0;
    assert(decode(concatenated) > 0);
    assert(invalidConcatenated > 0);
    std::puts("PASS: valid MP3 decodes without false concatenation warning; real concatenation still warns");
}
'''


def main():
    if not shutil.which('ffmpeg'):
        raise SystemExit('ffmpeg is required')
    include = os.environ.get('GX_FFMPEG_INCLUDE_DIR')
    if include:
        ffmpeg_flags = ['-I', include]
    else:
        ffmpeg_flags = subprocess.check_output(
            ['pkg-config', '--cflags', 'libavformat', 'libavcodec', 'libavutil'],
            text=True).split()
    libraries = []
    for library in ('avformat', 'avcodec', 'avutil'):
        soname = ctypes.util.find_library(library)
        if soname is None:
            raise SystemExit(f'lib{library} is required')
        libraries.append('-l:' + soname)
    with tempfile.TemporaryDirectory(prefix='gx-ffmpeg-size-') as directory:
        temp = Path(directory)
        (temp/'Lib').mkdir()
        (temp/'Common').mkdir()
        (temp/'Lib/BaseType.h').write_text(TYPES)
        (temp/'always.h').write_text(TYPES)
        (temp/'GXTrace.h').write_text(TYPES)
        (temp/'Common/file.h').write_text(FILE_ADAPTER)
        (temp/'test.cpp').write_text(HARNESS)
        tone = temp/'tone.mp3'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-f', 'lavfi',
                        '-i', 'sine=frequency=440:duration=1', '-c:a', 'libmp3lame',
                        '-q:a', '2', str(tone)], check=True)
        for path in ('Core/GameEngineDevice', 'GeneralsMD/Code/GameEngineDevice'):
            executable = temp/'test'
            subprocess.run([os.environ.get('CXX', 'c++'), '-std=c++17', '-O1',
                            '-Wall', '-Wextra', '-Wno-sign-compare',
                            '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                            '-I', str(temp), '-I', str(ROOT/path/'Include'),
                            *ffmpeg_flags,
                            str(ROOT/path/'Source/VideoDevice/FFmpeg/FFmpegFile.cpp'),
                            str(temp/'test.cpp'), *libraries, '-o', str(executable)], check=True)
            print(path, flush=True)
            subprocess.run([str(executable), str(tone)], check=True)


if __name__ == '__main__':
    main()
