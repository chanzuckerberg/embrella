
### HELPFUL #################################################
.PHONY: help
help: ## display help for this makefile
	@echo "Usage: make [target]\n"
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

### LOCAL DEVELOPMENT ######################################
.PHONY: start
start: ## Start the embrella development environment
	python manage.py runserver

.PHONE: db-migrate
db-migrate: ## Migrate the database
	python manage.py migrate
