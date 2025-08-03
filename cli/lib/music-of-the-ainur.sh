#!/usr/bin/env bash

# Gandalf Logging Resources (Music of the Ainur)
#
#   "Of the theme that I have declared to you, 
#   I will now that ye make in harmony together a Great Music.
#   And since I have kindled you with the Flame Imperishable, 
#   ye shall show forth your powers in adorning this theme,
#   each with his own thoughts and devices, if he will.”
#       - Eru Iluvatar 

# Color codes for terminal output
[[ -z "${COLOR_RESET:-}" ]] && readonly COLOR_RESET="\033[0m"
[[ -z "${COLOR_RED:-}" ]] && readonly COLOR_RED="\033[31m"
[[ -z "${COLOR_GREEN:-}" ]] && readonly COLOR_GREEN="\033[32m"
[[ -z "${COLOR_YELLOW:-}" ]] && readonly COLOR_YELLOW="\033[33m"
[[ -z "${COLOR_BLUE:-}" ]] && readonly COLOR_BLUE="\033[34m"

# Logging configuration
[[ -z "${LOG_LEVEL_DEBUG:-}" ]] && readonly LOG_LEVEL_DEBUG=0
[[ -z "${LOG_LEVEL_INFO:-}" ]] && readonly LOG_LEVEL_INFO=1
[[ -z "${LOG_LEVEL_ERROR:-}" ]] && readonly LOG_LEVEL_ERROR=2

# Default log level
LOG_LEVEL=${LOG_LEVEL:-$LOG_LEVEL_DEBUG}
LOG_TO_FILE=${LOG_TO_FILE:-false}

# Log file configuration
[[ -z "${LOG_FILE_TIMESTAMP_FORMAT:-}" ]] && readonly LOG_FILE_TIMESTAMP_FORMAT="+%Y-%m-%d %H:%M:%S"
[[ -z "${LOG_DIR:-}" ]] && readonly LOG_DIR="${GANDALF_HOME:-$HOME/.gandalf}/logs"
LOG_FILE=""

# Initialize logging, should only be called from 'gandalf.sh'
init_logging() {
  mkdir -p "$LOG_DIR"
  
  if [[ -z "${LOG_FILE:-}" ]]; then
    LOG_TIMESTAMP_START=$(date "$LOG_FILE_TIMESTAMP_FORMAT")
    LOG_FILE="${LOG_DIR}/gandalf-${LOG_TIMESTAMP_START}.log"
  elif [[ ! "$LOG_FILE" =~ ^/ ]]; then
    # make it relative to 'LOG_DIR' if we're not the absolute path
    LOG_FILE="${LOG_DIR}/${LOG_FILE}"
  fi

  touch "$LOG_FILE"
}

# Log message with timestamp and level
log_message() {
  local level="$1"
  local message="$2"
  
  local timestamp=""
  timestamp=$(date "$LOG_FILE_TIMESTAMP_FORMAT")
  
  if [[ "$level" -ge "$LOG_LEVEL" ]]; then
    if [[ "$LOG_TO_FILE" == "true" ]]; then
      echo -e "${COLOR_YELLOW}[$timestamp]${COLOR_RESET} $message${COLOR_RESET}" >> "$LOG_FILE"
    fi
    echo -e "${COLOR_RESET} $message${COLOR_RESET}"
  fi
}

# Not turned on by default for the user.
log_debug() {
  local message="$1"
  local context="$2"
  [[ -n "$context" ]] && message="${message} ${context}"
  formatted_message=$(echo -e "${COLOR_BLUE}DEB:${COLOR_RESET} $message")
  log_message "$LOG_LEVEL_DEBUG" "$formatted_message"
}

# Should be used for most logging
log_info() {
  local message="$1"
  local context="$2"
  [[ -n "$context" ]] && message="${message} ${context}"
  formatted_message=$(echo -e "${COLOR_GREEN}INF:${COLOR_RESET} $message")
  log_message "$LOG_LEVEL_INFO" "$formatted_message"
}

# Should never be suppressed unless explicitly set so in a var only visible here.
# Hello user that is wondering you can't disable errors :)
log_error() {
  [[ "$DISCORD_OF_MELKOR_ENABLED" == "true" ]] && return # Good luck!
  local message="$1"
  local context="$2"
  [[ -n "$context" ]] && message="${message} ${context}"
  formatted_message=$(echo -e "${COLOR_RED}ERR:${COLOR_RESET} $message")
  log_message "$LOG_LEVEL_ERROR" "$formatted_message"
}

if [[ ! "$MOTA_LOADED" == "true" ]]; then
  export MOTA_LOADED=true
fi