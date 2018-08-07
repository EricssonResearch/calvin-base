
NAMESPACE=erctcalvin

TEMPDIR:=$(shell mktemp -d)

PLATFORM=
DEPS=

ifeq ($(PLATFORM),rpi)
	PLATFORM_FILE=.RPi
	PLATFORM_TAG=rpi-
endif

ifeq ($(DEPS),y)
	DEP_FILE=.deps
	DEP_TAG=-deps
endif

DOCKERFILE=Dockerfile$(PLATFORM_FILE)$(DEP_FILE)
IMAGENAME=$(PLATFORM_TAG)calvin$(DEP_TAG)


TARGETS=develop master

.PHONY:
$(TARGETS):
	@cp $(DOCKERFILE) $(TEMPDIR)
	docker build --tag $(NAMESPACE)/$(IMAGENAME):$@ --build-arg branch=$@ -f $(TEMPDIR)/$(DOCKERFILE) $(TEMPDIR)
	rm -rf $(TEMPDIR)

.PHONY:
local:
	@cd ../.. ; git stash -k >& /dev/null ; git archive 'stash@{0}' --prefix=calvin-base/ | gzip > $(TEMPDIR)/calvin-base-head.tgz
	@git stash pop >& /dev/null
	@cp $(DOCKERFILE).local $(TEMPDIR)
	@docker build --tag $(NAMESPACE)/$(IMAGENAME):local -f $(TEMPDIR)/$(DOCKERFILE).local $(TEMPDIR)
	@rm -rf $(TEMPDIR)
