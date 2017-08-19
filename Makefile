
.PHONY: __default
__default:
	@echo "Available targets:"
	@echo "- test"

.PHONY: test
test:
	nodepy-nosetests test/*
