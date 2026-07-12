cmake_minimum_required(VERSION 4.0)
project(regex)

set(REGEX_SOURCES
	regcomp.c
	regerror.c
	regexec.c
	regfree.c
)

set(REGEX_HEADERS
	cclass.h
	cname.h
	regex.h
	regex2.h
	utils.h
)

add_library(regex ${REGEX_SOURCES} ${REGEX_HEADERS})

install(TARGETS regex LIBRARY DESTINATION "${CMAKE_INSTALL_PREFIX}/lib")
install(FILES ${REGEX_HEADERS} DESTINATION "${CMAKE_INSTALL_PREFIX}/include")
