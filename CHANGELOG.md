# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Configurable retry strategies: exponential backoff and constant (the default)
    - Configurable delay between attempt (default 60 seconds)
    - Configurable max attempts before error (default 6)
- Configurable Apprise summary: every run or on error if there's remaining searches after running
    - Also configurable as a script parameter that takes precedence (useful for development)
- Some useful JetBrains config
- More logging
- More type hints
- Defaults when getting config

### Changed

- Simplified search logic and made more resilient
    - Added assertion that terms were correctly typed
- Persist and read Google trends from disk for a given day (helps get rid of duplicate searches even between different
  runs)

### Removed

- Redundant calls to close Chrome
- Calls to close all Chrome processes

### Fixed

- Error when executing script from .bat file #113 Reference paths independent of pwd
- [BUG] AttributeError: 'Browser' object has no attribute 'giveMeProxy' #115 Comment out and todo give me proxy
- When logger is set to debug, doesn't include library code now
- [BUG] SessionNotCreatedException on Mobile Browser Creation #126 Sleep a bit after closing browser so ports are freed
  up

## [0.0.0] - 2023-03-05

### Added

- Farmer and lots of other things, but gotta start a changelog somewhere!