#!/usr/bin/env python3
"""Static + software equivalence tests for the Android GLES terrain fusion."""
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[2]
shader = (ROOT / "Core/GameEngineDevice/Source/W3DDevice/GameClient/W3DShaderManager.cpp").read_text()
gles = (ROOT / "Core/Libraries/Source/d3d8gles/src/gles_pipeline.cpp").read_text()
height = (ROOT / "Core/GameEngineDevice/Source/W3DDevice/GameClient/HeightMap.cpp").read_text()


def mul(a, b):
    return tuple(x * y for x, y in zip(a, b))


def legacy(base, alpha, diffuse):
    dst = mul(base, diffuse)
    src = mul(alpha, diffuse)
    sa = src[3]
    # D3DRS_SRCBLEND=SRCALPHA, D3DRS_DESTBLEND=INVSRCALPHA.
    return tuple(src[i] * sa + dst[i] * (1.0 - sa) for i in range(4))


def fused(base, alpha, diffuse):
    dst = mul(base, diffuse)
    src = mul(alpha, diffuse)
    sa = max(0.0, min(1.0, alpha[3] * diffuse[3]))
    return tuple(dst[i] * (1.0 - sa) + src[i] * sa for i in range(4))


def main():
    required_shader = [
        "class TerrainShaderGLESFused",
        "GX_D3DTOP_TERRAIN_ALPHA_BLEND",
        "W3DShadersPassCount[W3DShaderManager::ST_TERRAIN_BASE]=1",
        "W3DShadersPassCount[W3DShaderManager::ST_TERRAIN_BASE_NOISE1]=2",
        "W3DShadersPassCount[W3DShaderManager::ST_TERRAIN_BASE_NOISE2]=2",
        "W3DShadersPassCount[W3DShaderManager::ST_TERRAIN_BASE_NOISE12]=2",
        "D3DRS_ALPHABLENDENABLE, false",
    ]
    for marker in required_shader:
        assert marker in shader, marker
    assert "if (!d3d8gles_ShouldUseVulkanBackend() && terrainShader2Stage.init())" in shader
    assert "SRCALPHA/INVSRCALPHA" in gles
    assert "mix(%s, (%s * vCol), clamp((%s) * vCol.a" in gles
    assert "setTexture(1,m_stageOneTexture)" in height

    rng = random.Random(0x54455252)
    for _ in range(100_000):
        base = tuple(rng.random() for _ in range(4))
        alpha = tuple(rng.random() for _ in range(4))
        diffuse = tuple(rng.random() for _ in range(4))
        a = legacy(base, alpha, diffuse)
        b = fused(base, alpha, diffuse)
        # Terrain explicitly disables destination-alpha writes in Render();
        # compare the visible RGB result, which is the SRCALPHA equation.
        assert max(abs(a[i] - b[i]) for i in range(3)) < 1e-12, (a, b)

    # A cloud/noise shader retains an independent second pass; no texture
    # quality/resolution toggle is part of the implementation.
    assert "if (pass != 0)" in shader and "return terrainShader2Stage.set(2)" in shader
    assert "D3DTSS_ALPHAOP, D3DTOP_DISABLE" in shader
    assert "D3DCOLORWRITEENABLE_BLUE|D3DCOLORWRITEENABLE_GREEN|D3DCOLORWRITEENABLE_RED" in height
    print("PASS: 100000 random texels match SRCALPHA/INVSRCALPHA exactly")
    print("PASS: base/noise uses 1/2 passes and preserves the legacy noise pass")
    print("PASS: Android GLES runtime guard, alpha texture binding, and fallback markers present")


if __name__ == "__main__":
    main()
