# MSVC detection module

Detect available MSVC versions.

## Options

- `msvc.version` (int)
- `msvc.arch` (str)
- `msvc.platform_type` (str)
- `msvc.sdk_version` (str)
- `msvc.cache` (bool)

## MSVC Version Matrix

| Name               | \_MSC_VER | Shortcode | Version     |
| ------------------ | --------- | --------- | ----------- |
| Visual Studio 2017 | 1910      | v2017     | MSVC++ 14.1 |
| Visual Studio 2015 | 1900      | v140      | MSVC++ 14.0 |
| Visual Studio 2013 | 1800      | v120      | MSVC++ 12.0 |
| Visual Studio 2012 | 1700      | v110      | MSVC++ 11.0 |
| Visual Studio 2010 | 1600      | v100      | MSVC++ 10.0 |
| Visual Studio 2008 | 1500      |  v90      | MSVC++  9.0 |
| Visual Studio 2005 | 1400      |  v80      | MSVC++  8.0 |
| Visual Studio 2003 | 1310      |  v71\*    | MSVC++  7.1 |
| --                 | 1300      |  v70\*    | MSVC++  7.0 |
| --                 | 1200      |  v60\*    | MSVC++  6.0 |
| --                 | 1100      |  v50\*    | MSVC++  5.0 |
