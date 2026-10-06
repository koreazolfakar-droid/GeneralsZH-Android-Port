# Create gitinfo.cpp
# GeneralsX @build Codex 05/10/2026 Older cached workflows have depth-one source
# checkouts. Recover history before check_git generates the native GitRevision.
if(ANDROID)
    execute_process(
        COMMAND bash "${CMAKE_SOURCE_DIR}/scripts/build/android/prepare-engine-history.sh" "${CMAKE_SOURCE_DIR}"
        RESULT_VARIABLE ENGINE_HISTORY_RESULT)
    if(NOT ENGINE_HISTORY_RESULT EQUAL 0)
        message(FATAL_ERROR "Android engine version requires complete source Git history")
    endif()
endif()
set(GIT_PRE_CONFIGURE_FILE "${CMAKE_CURRENT_SOURCE_DIR}/gitinfo/gitinfo.cpp.in")
set(GIT_POST_CONFIGURE_FILE "${CMAKE_CURRENT_BINARY_DIR}/gitinfo.cpp")

include(gitinfo/git_watcher.cmake)

# Create resources library
add_library(resources STATIC)

target_sources(resources PRIVATE
    "${CMAKE_CURRENT_BINARY_DIR}/gitinfo.cpp"
    gitinfo/gitinfo.h
)

target_include_directories(resources PUBLIC
    gitinfo
)

# Add resources (optional)
if (MSVC_IDE)
    target_sources(resources PRIVATE
        visualstudio/asciistring.natvis
        visualstudio/stllist.natvis
        visualstudio/stlvector.natvis
        visualstudio/unicodestring.natvis
    )
endif()
