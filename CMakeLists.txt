cmake_minimum_required ( VERSION 2.8 )

option ( BUILD_PYTHON                 "Build the python module for the library"                               ON )
option ( BUILD_DOC                    "Build the documentation"                                               ON )
option ( USE_SSH                      "Enable remote tests through ssh"                                       OFF )

project ( OTDistFunc CXX )

string ( TOLOWER ${CMAKE_PROJECT_NAME} PACKAGE_NAME )

# set module dir to find custom scripts
list ( APPEND CMAKE_MODULE_PATH ${CMAKE_SOURCE_DIR}/cmake )

set ( OTDISTFUNC_DATA_PATH share )
set ( OTDISTFUNC_EXAMPLE_PATH ${OTDISTFUNC_DATA_PATH}/${PACKAGE_NAME}/examples )
set ( OTDISTFUNC_CONFIG_CMAKE_PATH lib${LIB_SUFFIX}/cmake/otdistfunc )
set ( DOC_INSTALL_PATH share/doc/${PACKAGE_NAME} )

find_package (OpenTURNS NO_MODULE REQUIRED)
if (OPENTURNS_FOUND)
  message (STATUS "Found OpenTURNS: ${OPENTURNS_ROOT_DIR}")
  set (OPENTURNS_VERSION ${OPENTURNS_VERSION_STRING})
endif ()

if ( USE_SSH )
  find_program ( SSH_EXECUTABLE NAMES ssh )
endif ()

if ( BUILD_PYTHON )
  find_package ( PythonInterp )
  include ( FindPythonModule )
  find_python_module ( argparse )
  if ( PYTHONINTERP_FOUND )
    execute_process ( COMMAND ${PYTHON_EXECUTABLE} -c "from distutils import sysconfig; print(sysconfig.get_python_lib( plat_specific=False, prefix='${CMAKE_INSTALL_PREFIX}'))"
                      OUTPUT_VARIABLE _ABS_PYTHON_MODULE_PATH
                      RESULT_VARIABLE _PYTHON_pythonlib_result 
                      OUTPUT_STRIP_TRAILING_WHITESPACE )

    if (NOT _PYTHON_pythonlib_result) 
      get_filename_component ( _ABS_PYTHON_MODULE_PATH ${_ABS_PYTHON_MODULE_PATH} ABSOLUTE )
      file ( RELATIVE_PATH _REL_PYTHON_MODULE_PATH ${CMAKE_INSTALL_PREFIX} ${_ABS_PYTHON_MODULE_PATH} )                   

      set ( OTDISTFUNC_PYTHON_MODULE_PATH
            ${_REL_PYTHON_MODULE_PATH}
            CACHE PATH "The directory where the python modules are installed"
          )

    else ()
      message ( SEND_ERROR "Could not run ${PYTHON_EXECUTABLE}" ) 
    endif ()

    if (CMAKE_VERSION VERSION_LESS "2.8.6")
      execute_process (COMMAND ${PYTHON_EXECUTABLE} -c "import sys; print(sys.version_info[0])"
                       OUTPUT_VARIABLE PYTHON_VERSION_MAJOR
                       OUTPUT_STRIP_TRAILING_WHITESPACE)
    endif ()
    set (OTDISTFUNC_PYTHON${PYTHON_VERSION_MAJOR}_MODULE_PATH ${OTDISTFUNC_PYTHON_MODULE_PATH})
  endif ( PYTHONINTERP_FOUND )
endif ()


# WARNING: This is where variables without OPENTURNS_ prefix are defined !
foreach ( _var PYTHON_MODULE_PATH LIBRARY_PATH INCLUDE_PATH )
  if ( NOT IS_ABSOLUTE OTDISTFUNC_${_var} )
    set ( OTDISTFUNC_${_var} ${CMAKE_INSTALL_PREFIX}/${OTDISTFUNC_${_var}} )
  endif ()
  set ( ${_var} ${OTDISTFUNC_${_var}} )
endforeach ( _var )


# The tests can't be run if this function is absent
enable_testing ()
add_custom_target ( tests COMMENT "Build tests" )
add_custom_target ( check COMMENT "Run pre-installation tests" )
add_custom_target ( installcheck COMMENT "Run post-installation tests" )

add_dependencies ( check cppcheck )

if ( PYTHONINTERP_FOUND )
  add_subdirectory ( python )
  add_dependencies ( installcheck pyinstallcheck )
endif ()

set ( CPACK_PACKAGE_NAME          ${PACKAGE_NAME} )
set ( CPACK_PACKAGE_VERSION_MAJOR 0              )
set ( CPACK_PACKAGE_VERSION_MINOR 4h              )
set ( CPACK_PACKAGE_VERSION_PATCH                )
set ( CPACK_SOURCE_GENERATOR      "TGZ;TBZ2"     )
set ( CPACK_BINARY_STGZ           "OFF"          )
set ( CPACK_BINARY_TBZ2           "ON"           )
set ( CPACK_BINARY_TGZ            "ON"           )
set ( CPACK_BINARY_TZ             "OFF"          )
set ( CPACK_SOURCE_IGNORE_FILES "/.svn;/build;.*~;${CPACK_SOURCE_IGNORE_FILES}" )
set ( PACKAGE_NAME           ${CPACK_PACKAGE_NAME} )
set ( PACKAGE_VERSION        ${CPACK_PACKAGE_VERSION_MAJOR}.${CPACK_PACKAGE_VERSION_MINOR} )
if ( CPACK_PACKAGE_VERSION_PATCH )
  set ( PACKAGE_VERSION       ${PACKAGE_VERSION}.${CPACK_PACKAGE_VERSION_PATCH} )
endif ()
set ( CPACK_SOURCE_PACKAGE_FILE_NAME ${PACKAGE_NAME}-${PACKAGE_VERSION} )
include ( CPack )

# uninstall target
configure_file (
  ${CMAKE_CURRENT_SOURCE_DIR}/cmake/cmake_uninstall.cmake.in
  ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake
  IMMEDIATE @ONLY
)

add_custom_target ( uninstall
  COMMAND ${CMAKE_COMMAND} -P ${CMAKE_CURRENT_BINARY_DIR}/cmake_uninstall.cmake
)

if ( BUILD_DOC )
  add_subdirectory ( doc )
endif ()
