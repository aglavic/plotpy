#!/bin/bash
# Script to update the repository contents with the latest verstion of the plot script package
# Build binary distribution
cd ..
# create Python 2.6 package:
cd archiv
FILE=`ls -t *_maverick.deb| head -1`
FILE_ALL=`echo $FILE|sed 's/_maverick.deb//'`_all.deb
cp -u $FILE ../repository/binary/dists/maverick/$FILE_ALL
# create Python 2.7 package:
FILE=`ls -t *_natty.deb| head -1`
FILE_ALL=`echo $FILE|sed 's/_natty.deb//'`_all.deb
cp -u $FILE ../repository/binary/dists/natty/$FILE_ALL

cd ../repository
# Repo update
apt-ftparchive generate ftparchive.conf
apt-ftparchive -c ftparchive_maverick.conf release dists/maverick/> dists/maverick/Release
apt-ftparchive -c ftparchive_natty.conf release dists/natty/> dists/natty/Release
rm dists/maverick/Release.gpg dists/natty/Release.gpg
gpg -sba -o dists/maverick/Release.gpg dists/maverick/Release
gpg -sba -o dists/natty/Release.gpg dists/natty/Release
# sync with server
rsync -ruvz --delete * aglavic@web.sourceforge.net:/home/project-web/plotpy/htdocs/repository
