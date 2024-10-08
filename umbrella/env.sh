#!/bin/bash

save_env_variables() {
    grep -v '^#' .env | xargs -I {} echo "export {}" >> ~/.bashrc
    echo "Environment variables have been successfully loaded from .env"
}


save_env_variables


