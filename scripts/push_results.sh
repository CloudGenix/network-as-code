#!/bin/bash
#
# Push Results from previous scripts.
# Update 'in_prod' if successful.
#
# Script assumes CWD is a git repo and has the branch/commit that should be compared to 'in_prod' checked out.
# Script also assumes cloudgenix_config is installed and working (pip install cloudgenix_config)
#
# Variables expected set by the CI/CD before this script:
# AUTH_TOKEN = Valid tenant_super CloudGenix Auth Token
# GITHUB_REPO_TOKEN = Valid personal token that has Repository access to commit.

# load the common vars
. scripts/script_includes.source

# push logs and screenshots to results repository
echo -e "${WHITE}Pushing results to origin/results.. ${NC}"
git add -A logs/* 2>&1 | indent
git add -A screenshots/* 2>&1 | indent
git commit -m 'Configuration Log and Screenshot Results [ci skip]' 2>&1 | indent
git push origin results 2>&1 | indent

## Debug push items
#git log --full-history
#git reflog
#git remote -v

if [ "${EXIT_CODE}" == 0 ]
  then
    echo -e "${GREEN}Finished! (Success)${NC}"
  else
    echo -e "${RED}Finished! (Failed)${NC}"
fi
exit "${EXIT_CODE}"

