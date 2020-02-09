#!/bin/bash
#
# Execute all config changes in a repo from the last 'in_prod' tag.
# Update 'in_prod' if successful, and old 'in_prod' goes to 'prev_prod'.
#
# Script assumes CWD is a git repo and has the branch/commit that should be compared to 'in_prod' checked out.
# Script also assumes cloudgenix_config is installed and working (pip install cloudgenix_config)
#
# Variables expected set by the CI/CD before this script:
# AUTH_TOKEN = Valid tenant_super CloudGenix Auth Token
# GITHUB_REPO_TOKEN = Valid personal token that has Repository access to commit.

# load the common vars
. scripts/script_includes.source

# Set up git for log commit back to master.
echo -e "${WHITE}Setting GIT authentication/origin..${NC}"
git config --global user.email "travis-worker-cloudgenix@travis-ci.org" 2>&1 2>&1 | indent
git config --global user.name "travis-worker-cloudgenix" 2>&1 | indent

# Remove existing "origin"
git remote rm origin 2>&1 | indent
# Add new "origin" with access token in the git URL for authentication
git remote add origin "https://travis-worker-cloudgenix:${GITHUB_REPO_TOKEN}@github.com/CloudGenix/network-as-code.git" > /dev/null 2>&1

## DEBUG - find out why things arent working
#git remote get-url --all origin
#git show-ref -s in_prod

# Get latest commit tagged in production.
CGX_COMMIT_IN_PROD=$(git show-ref -s in_prod)
echo -e "${WHITE}Current 'in_prod' commit:${NC} ${CGX_COMMIT_IN_PROD}"

# Get commit previously in production.
CGX_COMMIT_PREV_PROD=$(git show-ref -s prev_prod)
echo -e "${WHITE}Current 'prev_prod' commit:${NC} ${CGX_COMMIT_PREV_PROD}"

# Get modified from current master commit and latest in_prod commit.
MODIFIED_CONFIGS=$(git diff "${CGX_COMMIT_IN_PROD}" "${CI_COMMIT}" --diff-filter=ACMR --name-status | cut -f2 \
                   | grep 'configurations\/.*\.yml')

# execute the changes
echo -e "${WHITE}Commit diff check range:${NC} ${CGX_COMMIT_IN_PROD}...${CI_COMMIT}"
echo -e "${WHITE}Configuration Files Added or Modified:${NC}"
echo "${MODIFIED_CONFIGS}" 2>&1 | indent

# create tmp logs
mkdir -p /tmp/logs

for SITE_CONFIG in ${MODIFIED_CONFIGS}
  do
    SITE_CONFIG_FILE=$(basename "${SITE_CONFIG}")
    echo -e -n "${WHITE}Executing ${SITE_CONFIG_FILE} Configuration: ${NC}"
    # Do the actual site config operations.
    if do_site "${SITE_CONFIG}" > "/tmp/logs/${SITE_CONFIG_FILE}.log" 2>&1
      then
        echo -e "${GREEN}Success. ${NC}"
      else
        echo -e "${RED}Failed, code $?. ${NC}"
        EXIT_CODE=1
    fi
  done

# check status, don't update tags if one of the config pushes failed.
if [ ${EXIT_CODE} == 0 ]
  then
    # delete current prev_prod dag
    echo -e "${WHITE}Updating 'prev_prod' tag in Github..${NC}"
    git tag -d prev_prod 2>&1 | indent
    git push origin :refs/tags/prev_prod 2>&1 | indent

    # add new prev_prod tag to current build
    git tag prev_prod "${CGX_COMMIT_IN_PROD}" 2>&1 | indent
    git push origin refs/tags/prev_prod 2>&1 | indent

    # delete current in_prod tag
    echo -e "${WHITE}Updating 'in_prod' tag in Github..${NC}"
    git tag -d in_prod 2>&1 | indent
    git push origin :refs/tags/in_prod 2>&1 | indent

    # add new in_prod tag to current build
    git tag in_prod 2>&1 | indent
    git push origin refs/tags/in_prod 2>&1 | indent

  else
    # deploy to prod failed. Do not update tag so it will be tried again.
    echo -e "${RED}ERROR: One or more cloudgenix_config items failed. Preserving existing 'in_prod' and 'prev_prod' tags.${NC}"
    echo -e "${RED}    'in_prod': ${CGX_COMMIT_IN_PROD}${NC}"
    echo -e "${RED}  'prev_prod': ${CGX_COMMIT_PREV_PROD}${NC}"
    echo -e "${RED}Please review build logs, origin/results logs. Build can be re-run, or will automatically with a new pull to fix the issue(s)."
fi

# switch to logs
echo -e "${WHITE}Preping to save logs to origin/results.. ${NC}"
git checkout -b results 2>&1 | indent
git fetch --all 2>&1 | indent
git branch -u origin/results 2>&1 | indent
git reset --hard origin/results 2>&1 | indent

# merge (w/overwrite) master to logs.
git pull --no-commit -X theirs origin master 2>&1 | indent

# copy logs to logs directory
echo -e "${WHITE}Updating logs/ with new logs..${NC}"
cp -av /tmp/logs/* logs/ 2>&1 | indent

## push logs to results repository. Using 2nd script for screenshots, uncomment this if you want deploy_changes.sh to be
## standalone.
#echo -e "${WHITE}Pushing results to origin/results.. ${NC}"
#git add -A logs/* 2>&1 | indent
#git add -A screenshots/* 2>&1 | indent
#git commit -m 'Configuration Log and Screenshot Results [ci skip]' 2>&1 | indent
#git push origin results 2>&1 | indent

## Debug push items
#git log --full-history
#git reflog
#git remote -v

# save changed files for later scripts.
echo "${MODIFIED_CONFIGS}" > .tmp_modified_configs.txt

if [ "${EXIT_CODE}" == 0 ]
  then
    echo -e "${GREEN}Finished! (Success)${NC}"
  else
    echo -e "${RED}Finished! (Failed)${NC}"
fi
exit "${EXIT_CODE}"

