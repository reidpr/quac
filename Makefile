README.html: README
	sed -e 's/\(\(  \)\+\)/\1\1/g' -e 's/^\( *\)+/\11./' < README | markdown_py -x toc /dev/stdin > README.html
