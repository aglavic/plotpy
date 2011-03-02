#!/bin/bash
# Script to update the repository contents with the latest verstion of the plot script package
# Copy latest .deb file
cd ../archiv
FILE=`ls -t *.deb| head -1`
cd ../repository
FILE_ALL=`echo $FILE|sed 's/.deb//'`_all.deb
cp ../archiv/$FILE binary/$FILE_ALL
apt-ftparchive generate ftparchive.conf
apt-ftparchive -c ftparchive.conf release dists/maverick/> dists/maverick/Release
gpg -sba -o dists/maverick/Release.gpg dists/maverick/Release
# sync with server
rsync -ruvz * ifflinux.iff.kfa-juelich.de:public_html/plotrepo
