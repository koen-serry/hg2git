from mercurial import ui, hg
import datetime,os,re,sys 

def getgitenv(user, date):
    env = ''
    elems = re.compile('(.*?)\s+<(.*)>').match(user)
    if elems:
        env += 'export GIT_AUTHOR_NAME="%s" ;' % elems.group(1)
        env += 'export GIT_COMMITER_NAME="%s" ;' % elems.group(1)
        env += 'export GIT_AUTHOR_EMAIL="%s" ;' % elems.group(2)
        env += 'export GIT_COMMITER_EMAIL="%s" ;' % elems.group(2)
    else:
        env += 'export GIT_AUTHOR_NAME="%s" ;' % user
        env += 'export GIT_COMMITER_NAME="%s" ;' % user
        env += 'export GIT_AUTHOR_EMAIL= ;'
        env += 'export GIT_COMMITER_EMAIL= ;'
    env += 'export GIT_AUTHOR_DATE="%s" ;' % date
    env += 'export GIT_COMMITTER_DATE="%s" ;' % date
    return env

def oscmd(cmd):
	print 'OS -> ',cmd
	os.system(cmd)

hgprj = sys.argv[1]
os.chdir(hgprj)

	
# Maps hg version -> git version
hgvers = {}
# List of children for each hg revision
hgchildren = {}
# Current branch for each hg revision
current_branch = ''
repo = hg.repository(ui.ui(), '.')
gitbranches = ['master']

print 'creating repository'
oscmd('git-init-db')

for change in repo.changelog:
	ctx = repo.changectx(change)
	
	date = datetime.datetime.fromtimestamp(ctx.date()[0])
	parents = map(lambda x: x.rev(), ctx.parents())	
	branch = 'master' if ctx.branch()=='default' else ctx.branch()
	print '-----------------------------------------'
	print 'cset:', change
	print 'branch:', branch
	print 'user:', ctx.user()
	print 'date:', date
	print 'comment:', ctx.description()
	print 'parent:', parents
	print 'tag:', ctx.tags()
	print '-----------------------------------------'	
	if branch != current_branch:
		try:
			gitbranches.index(branch)
		except:
			print 'creating new branch', branch
			oscmd('git-checkout -b %s %s' % (branch, change))
			current_branch = branch
			gitbranches.append( current_branch )
	else:
		print 'checking out branch', branch
		oscmd('git-checkout %s' % branch)

	# merge
	otherbranch = ''
	if len(parents) > 1:
		for parent in parents:
			otherbranch = 'master' if repo.changectx(parent).branch()=='default' else repo.changectx(parent).branch()
			if otherbranch != branch:
				print 'merging', otherbranch , 'into', branch
				oscmd(getgitenv(ctx.user(), date) + 'git-merge --no-commit -s ours %s %s' % (branch, otherbranch))
			

	# remove everything except .git and .hg directories
	oscmd('find . \( -path "./.hg" -o -path "./.git" \) -prune -o ! -name "." -print | xargs rm -rf')

	# repopulate with checkouted files
	oscmd('hg update -C %d' % change)

	# add new files
	oscmd('git-ls-files -x .hg --others | git-update-index --add --stdin')
	# delete removed files
	oscmd('git-ls-files -x .hg --deleted | git-update-index --remove --stdin')

	# commit
	oscmd(getgitenv(ctx.user(), date) + 'git-commit -a -m "%s"' % ctx.description())

	# if change == 0 > create the branch
	if change == 0:
		oscmd('git-checkout -b %s' % branch)

	# tag
	for tag in ctx.tags():
		if tag != 'tip':
			oscmd(getgitenv(ctx.user(), date) + 'git-tag "%s"' % tag.replace(' ','_'))

	# delete branch if not used anymore...
	if otherbranch != '':
		print "Deleting unused branch:", otherbranch
		oscmd('git-branch -d "%s"' % otherbranch)

	# retrieve and record the version
	vvv = os.popen('git-show | head -1').read()
	vvv = vvv[vvv.index(' ') + 1 : ].strip()
	print 'record', change, '->', vvv
	hgvers[change] = vvv

oscmd('git-repack -a -d')
