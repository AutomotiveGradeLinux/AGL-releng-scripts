#!/bin/sh

# scan remaining artifacts for generating jobs
# if LAVA_URL is set in testenv, all generated jobs are sent to LAVA

mkdir output

# hardcoded test

echo "TEST 1"
./utils/create-jobs.py --machine qemux86-64 --branch guppy --version latest --build-type ci \
	--changeid 1234 \
	--patchset 5678 \
	--applications-url https://download.automotivelinux.org/AGL/upload/ci/20581/1/guppy/x86-64/ > output/test
echo "TEST 2"
./utils/create-jobs.py --machine raspberrypi4 --branch guppy \
	--version latest \
	--build-type ci \
	--changeid 1234 \
	--patchset 5678 \
	--applications-url https://download.automotivelinux.org/AGL/upload/ci/20581/1/guppy/x86-64/ > output/test


CI=http://download.automotivelinux.org/AGL/upload/ci/

if [ -e testenv ];then
	#. $(pwd)/testenv
	echo "using env"
fi

wget -q $CI -O cilist || exit $?

grep -o "[0-9][0-9][0-9][0-9][0-9]*/" cilist | sort | uniq | sed 's,/$,,' |
while read CIID
do
	echo "$CIID"
	wget -q $CI/$CIID/ -O revid
	grep -o "[0-9][0-9]*/" revid | sort | uniq | sed 's,/$,,' |
	while read REVID
	do
		wget -q $CI/$CIID/$REVID -O machines
		grep -o '"[a-z0-9-][a-z0-9-]*/"' machines | cut -d'"' -f2 | sed 's,/$,,' |
		while read MACHINE
		do
			RMACHINE=$MACHINE
			case $MACHINE in
			h3ulcb-nogfx)
				RMACHINE=h3ulcb-kf
			;;
			master)
				# HACK: we are in a app
				continue
			;;
			esac
			echo "TEST: $CIID $REVID $MACHINE $RMACHINE"
			./utils/job-prereq.py --machine $RMACHINE --build-type ci $CIID $REVID --kernel || exit $?
			./utils/job-prereq.py --machine $RMACHINE --build-type ci $CIID $REVID --dtb || exit $?
			./utils/job-prereq.py --machine $RMACHINE --build-type ci $CIID $REVID --initrd || exit $?
			./utils/job-prereq.py --machine $RMACHINE --build-type ci $CIID $REVID --nbdroot || exit $?
			if [ -z "$LAVA_URL" ];then
				EXTRA_OPTS=""
			else
				EXTRA_OPTS="--callback-from lab-agl-core --callback-to Baylibre"
			fi
			./utils/create-jobs.py --machine $RMACHINE --build-type ci \
				--changeid $CIID --patchset $REVID $EXTRA_OPTS > output/job-$MACHINE
			if [ -z "$LAVA_URL" ];then
				continue
			fi
			if [ $MACHINE = 'qemuarm' -o $MACHINE = 'qemuarm64' -o $MACHINE = 'qemux86-64' ];then
				sed -i "s,job_name:.*,job_name: releng-test for $MACHINE ($CIID $REVID)," output/job-$MACHINE
				echo "SEND"
				lavacli --uri $LAVA_URL jobs submit output/job-$MACHINE > jobid
				if [ $? -eq 0 ];then
					lavacli --uri $LAVA_URL jobs wait $(cut -d' ' -f1 jobid)
					lavacli --uri $LAVA_URL jobs show $(cut -d' ' -f1 jobid)
				fi
				rm jobid
			fi
		done
		rm machines
	done
	rm revid
done

rm cilist

exit 0
