#pragma once

#include "Common/GameCommon.h"

// Upstream GeneralsX issue #65: visual-only conversion of 30/60Hz physics
// speed to the original 30Hz units used for wheel and tread dust.
// Scoped to the three vehicle draw modules; do not add this helper to
// GameCommon.h, because that invalidates hundreds of cached engine objects.
namespace GXFrameVisuals
{
inline Real retail30HzScale()
{
	return LOGICFRAMES_PER_SECONDS_REAL / (Real)BaseFps;
}
} // namespace GXFrameVisuals
