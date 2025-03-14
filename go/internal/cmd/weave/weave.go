// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// The weave command is a simple preprocessor for markdown files.
// It builds a table of contents and processes %include directives.
//
// Example usage:
//
//	$ go run internal/cmd/weave go-types.md > README.md
//
// The weave command copies lines of the input file to standard output, with two
// exceptions:
//
// If a line begins with "%toc", it is replaced with a table of contents
// consisting of links to the top two levels of headers ("#" and "##").
//
// If a line begins with "%include FILENAME TAG", it is replaced with the lines
// of the file between lines containing "!+TAG" and  "!-TAG". TAG can be omitted,
// in which case the delimiters are simply "!+" and "!-".
package main

// Modified from golang.org/x/example/internal/cmd/weave/weave.go.

import (
	"bufio"
	"bytes"
	"fmt"
	"log"
	"os"
	"regexp"
	"strings"
)

func main() {
	log.SetFlags(0)
	log.SetPrefix("weave: ")
	if len(os.Args) != 2 {
		log.Fatal("usage: weave input.md\n")
	}

	f, err := os.Open(os.Args[1])
	if err != nil {
		log.Fatal(err)
	}
	defer f.Close()

	fmt.Println("<!-- Autogenerated by weave; DO NOT EDIT -->")
	fmt.Println()

	// Pass 1: extract table of contents.
	var toc []string
	in := bufio.NewScanner(f)
	for in.Scan() {
		line := in.Text()
		if line == "" || (line[0] != '#' && line[0] != '%') {
			continue
		}
		line = strings.TrimSpace(line)
		if line == "%toc" {
			toc = nil
		} else if strings.HasPrefix(line, "# ") || strings.HasPrefix(line, "## ") {
			words := strings.Fields(line)
			depth := len(words[0])
			words = words[1:]
			text := strings.Join(words, " ")
			for i := range words {
				words[i] = strings.ToLower(words[i])
			}
			line = fmt.Sprintf("%s1. [%s](#%s)",
				strings.Repeat("\t", depth-1), text, strings.Join(words, "-"))
			toc = append(toc, line)
		}
	}
	if in.Err() != nil {
		log.Fatal(in.Err())
	}

	// Pass 2.
	if _, err := f.Seek(0, os.SEEK_SET); err != nil {
		log.Fatalf("can't rewind input: %v", err)
	}
	in = bufio.NewScanner(f)
	for in.Scan() {
		line := in.Text()
		tline := strings.TrimSpace(line)
		switch {
		case strings.HasPrefix(tline, "%toc"): // ToC
			for _, h := range toc {
				fmt.Println(h)
			}
		case strings.HasPrefix(tline, "%include"):
			// Indent the output by the whitespace preceding "%include".
			indent := line[:strings.IndexByte(line, '%')]
			words := strings.Fields(line)
			if len(words) < 2 {
				log.Fatal(line)
			}
			filename := words[1]

			section := ""
			if len(words) > 2 {
				section = words[2]
			}
			s, err := include(filename, section)
			if err != nil {
				log.Fatal(err)
			}
			fmt.Printf("%s```go\n", indent)
			fmt.Println(cleanListing(s, indent)) // TODO(adonovan): escape /^```/ in s
			fmt.Printf("%s```\n", indent)
		default:
			fmt.Println(line)
		}
	}
	if in.Err() != nil {
		log.Fatal(in.Err())
	}
}

// include processes an included file, and returns the included text.
// Only lines between those matching !+tag and !-tag will be returned.
// This is true even if tag=="".
func include(file, tag string) (string, error) {
	f, err := os.Open(file)
	if err != nil {
		return "", err
	}
	defer f.Close()

	startre, err := regexp.Compile("!\\+" + tag + "$")
	if err != nil {
		return "", err
	}
	endre, err := regexp.Compile("!\\-" + tag + "$")
	if err != nil {
		return "", err
	}

	var text bytes.Buffer
	in := bufio.NewScanner(f)
	var on bool
	for in.Scan() {
		line := in.Text()
		switch {
		case startre.MatchString(line):
			on = true
		case endre.MatchString(line):
			on = false
		case on:
			text.WriteByte('\t')
			text.WriteString(line)
			text.WriteByte('\n')
		}
	}
	if in.Err() != nil {
		return "", in.Err()
	}
	if text.Len() == 0 {
		return "", fmt.Errorf("no lines of %s matched tag %q", file, tag)
	}
	return text.String(), nil
}

func isBlank(line string) bool { return strings.TrimSpace(line) == "" }

func indented(line string) bool {
	return strings.HasPrefix(line, "    ") || strings.HasPrefix(line, "\t")
}

// cleanListing removes entirely blank leading and trailing lines from
// text, and removes n leading tabs.
// It then prefixes each non-blank line with indent.
func cleanListing(text, indent string) string {
	lines := strings.Split(text, "\n")

	// remove minimum number of leading tabs from all non-blank lines
	tabs := 999
	for i, line := range lines {
		if strings.TrimSpace(line) == "" {
			lines[i] = ""
		} else {
			if n := leadingTabs(line); n < tabs {
				tabs = n
			}
		}
	}
	for i, line := range lines {
		if line != "" {
			line := line[tabs:]
			lines[i] = line // remove leading tabs
		}
	}

	// remove leading blank lines
	for len(lines) > 0 && lines[0] == "" {
		lines = lines[1:]
	}
	// remove trailing blank lines
	for len(lines) > 0 && lines[len(lines)-1] == "" {
		lines = lines[:len(lines)-1]
	}
	// add indent
	for i, ln := range lines {
		if ln != "" {
			lines[i] = indent + ln
		}
	}
	return strings.Join(lines, "\n")
}

// leadingTabs counts the number of tabs that start s.
func leadingTabs(s string) int {
	var i int
	for i = 0; i < len(s); i++ {
		if s[i] != '\t' {
			break
		}
	}
	return i
}
