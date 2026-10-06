# Recovery-only dependency provider. Production source is never patched.
# Reuse actual verified link outputs; never invent objects or Ninja stamps.
include(FetchContent)
macro(gx_baseline_dependency method dependency)
  string(TOLOWER "${dependency}" _gx_dep)
  set(_gx_common "$ENV{GX_COMMON_BUILD}")
  set(_gx_assets "$ENV{GX_BASELINE_TOOLS}/assets")
  if(_gx_dep STREQUAL "adrenotools")
    if(NOT TARGET adrenotools)
      add_library(adrenotools SHARED IMPORTED GLOBAL)
      set_target_properties(adrenotools PROPERTIES
        IMPORTED_LOCATION "${_gx_assets}/libadrenotools.so"
        INTERFACE_INCLUDE_DIRECTORIES "${_gx_assets}/adrenotools/include")
    endif()
    FetchContent_SetPopulated(adrenotools SOURCE_DIR "${_gx_assets}/adrenotools" BINARY_DIR "${_gx_common}/_deps/adrenotools-reused")
  elseif("$ENV{GX_REUSE_RUNTIME}" STREQUAL "1")
    if(_gx_dep STREQUAL "sdl3")
      add_library(SDL3-shared SHARED IMPORTED GLOBAL)
      set_target_properties(SDL3-shared PROPERTIES IMPORTED_LOCATION "${_gx_common}/_deps/sdl3-build/libSDL3.so"
        INTERFACE_INCLUDE_DIRECTORIES "${_gx_common}/_deps/sdl3-src/include;${_gx_common}/_deps/sdl3-build/include")
      add_library(SDL3::SDL3 ALIAS SDL3-shared)
      add_library(SDL3::SDL3-shared ALIAS SDL3-shared)
      FetchContent_SetPopulated(SDL3 SOURCE_DIR "${_gx_common}/_deps/sdl3-src" BINARY_DIR "${_gx_common}/_deps/sdl3-build")
    elseif(_gx_dep STREQUAL "sdl3_image")
      add_library(SDL3_image::SDL3_image SHARED IMPORTED GLOBAL)
      set_target_properties(SDL3_image::SDL3_image PROPERTIES IMPORTED_LOCATION "${_gx_common}/_deps/sdl3_image-build/libSDL3_image.so"
        INTERFACE_INCLUDE_DIRECTORIES "${_gx_common}/_deps/sdl3_image-src/include" INTERFACE_LINK_LIBRARIES SDL3::SDL3)
      FetchContent_SetPopulated(SDL3_image SOURCE_DIR "${_gx_common}/_deps/sdl3_image-src" BINARY_DIR "${_gx_common}/_deps/sdl3_image-build")
    elseif(_gx_dep STREQUAL "openal_soft")
      add_library(OpenAL::OpenAL SHARED IMPORTED GLOBAL)
      set_target_properties(OpenAL::OpenAL PROPERTIES IMPORTED_LOCATION "${_gx_common}/_deps/openal_soft-build/libopenal.so"
        INTERFACE_INCLUDE_DIRECTORIES "${_gx_common}/_deps/openal_soft-src/include")
      FetchContent_SetPopulated(openal_soft SOURCE_DIR "${_gx_common}/_deps/openal_soft-src" BINARY_DIR "${_gx_common}/_deps/openal_soft-build")
    elseif(_gx_dep STREQUAL "gamespy")
      add_library(gamespy::gamespy SHARED IMPORTED GLOBAL)
      set_target_properties(gamespy::gamespy PROPERTIES IMPORTED_LOCATION "${_gx_common}/libgamespy.so"
        INTERFACE_INCLUDE_DIRECTORIES "${_gx_common}/_deps/gamespy-src/include;${_gx_common}/_deps/gamespy-src/include/gamespy")
      FetchContent_SetPopulated(gamespy SOURCE_DIR "${_gx_common}/_deps/gamespy-src" BINARY_DIR "${_gx_common}/_deps/gamespy-build")
    endif()
  endif()
endmacro()
cmake_language(SET_DEPENDENCY_PROVIDER gx_baseline_dependency SUPPORTED_METHODS FETCHCONTENT_MAKEAVAILABLE_SERIAL)
