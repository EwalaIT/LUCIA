# ##################################### #
#                                       #
#   How-To build this container image   #
#                                       #
# ##################################### #
#
#
# Local build
# -----------
# docker build \
#   -f iac/Dockerfile-ubuntu \
#   --build-arg VERSION=`cat src/mypkg/__init__.py | grep version | awk '{ print $3 }' |  tr -d '"'`  \
#   --build-arg GIT_BRANCH=`git branch --show-current` \
#   -t safebytelabs/PROJECTNAMEHERE:`cat src/mypkg/__init__.py | grep version | awk '{ print $3 }' |  tr -d '"'`  .
#
#
# Platform specific images (when you build for your own platform)
# ---------------------------------------------------------------
# docker build \
#   --build-arg BUILD_DATE=`date -u +"%Y-%m-%d"` \
#   --build-arg VERSION=`cat src/mypkg/__init__.py | grep version | awk '{ print $3 }' |  tr -d '"'`  \
#   --build-arg GIT_BRANCH=`git branch --show-current` \
#   -t safebytelabs/PROJECTNAMEHERE:`cat src/mypkg/__init__.py | grep version | awk '{ print $3 }' |  tr -d '"'` .
#
#
# Cross-compile platform independent images (when you use a build facility
# in your platform to cross-compile for another platform)
# ------------------------------------------------------------------------
# docker buildx ls
# docker buildx create --name testbuilder
# docker buildx use testbuilder
# docker buildx inspect --bootstrap
# docker buildx build \
#   --platform linux/arm/v6 \
#   --build-arg BUILD_DATE=`date -u +"%Y-%m-%d"` \
#   --build-arg VERSION=`cat src/mypkg/__init__.py | grep version | awk '{ print $3 }' |  tr -d '"'`  \
#   --build-arg GIT_BRANCH=`git branch --show-current` \
#   -t safebytelabs/PROJECTNAMEHERE:`cat src/mypkg/__init__.py | grep version | awk '{ print $3 }' |  tr -d '"'` --push .
#
