# Cyclc-Breaker

Some programming languages make it difficult to find cyclic references between different source files. Cycle-Breaker finds them.

## Supported programming languages

    * C
    * C++
    * Shell scripts

Support for Python and Ruby is planned for the next version. Need another language supported? Tell me!

## Features

    * Switch between JSON and human readable formating
    * Found cyclic references are printed in a format similar to that of a stack trace
    * Heuristic programming language detection if source file has no file suffix

## How does it work

Cyclic referencing in a directed graph is relatively easy to find using a depth search algorithm. When entering a new file recursively, you can either check whether the file has already been searched or simply descend and check whether a global recursive limit has been exceeded. Cycle-Breaker is currently using the second approach.
