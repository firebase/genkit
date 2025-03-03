// Copyright 2024 Google LLC
// SPDX-License-Identifier: Apache-2.0

// copy is a tool for copying parts of files.
// It reads a set of source files, collecting named sequences of lines to copy
// to a destination file.
// It then reads the destination files, replacing the named sections there, called sinks,
// with sections of the same name from the source files.
//
// Files involved in the copy contain comments of the form
//
//	//copy:COMMAND ARGS...
//
// There can't be spaces between the "//", the word "copy:", and the command name.
//
// Commands that appear in source files are:
//
//	start FILENAME NAME
//	   Start copying to the sink NAME in FILENAME.
//	stop
//	   Stop copying.
//
// Commands that appear in destination files are:
//
//	sink NAME
//	   Where to start copying lines marked with NAME.
//	endsink NAME
//	   Where to end a replacement. Inserted by the tool.
package main

import (
	"bytes"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"slices"
	"strings"

	"golang.org/x/exp/maps"
)

var (
	destDir = flag.String("dest", "", "destination directory")
)

func main() {
	flag.Parse()
	log.SetFlags(0)
	log.SetPrefix("copy: ")
	var chunks []*chunk
	for _, sourceFilename := range flag.Args() {
		cs, err := parseSourceFile(sourceFilename)
		if err != nil {
			log.Fatalf("%s: %v", sourceFilename, err)
		}
		chunks = append(chunks, cs...)
	}
	if err := writeChunks(chunks); err != nil {
		log.Fatal(err)
	}
}

type command struct {
	name string
	file string
	sink string
}

// A chunk is a sequence of bytes to be copied to a sink in a file.
type chunk struct {
	srcFile  string
	destFile string
	sink     string
	data     []byte
}

// parseSourceFile parses the named file into chunks.
func parseSourceFile(filename string) ([]*chunk, error) {
	data, err := os.ReadFile(filename)
	if err != nil {
		return nil, err
	}
	chunks, err := parseSource(data)
	if err != nil {
		return nil, err
	}
	dir := *destDir
	if dir == "" {
		dir = filepath.Dir(filename)
	}
	if err := setChunkFilenames(chunks, filename, dir); err != nil {
		return nil, err
	}
	return chunks, nil
}

// parseSource parses the contents of a source file into chunks.
func parseSource(src []byte) ([]*chunk, error) {
	lines := bytes.SplitAfter(src, []byte("\n"))
	var chunks []*chunk
	var curChunk *chunk
	for ln, line := range lines {
		cmd, err := parseCommand(line)
		if err != nil {
			return nil, fmt.Errorf("%d: %w", ln, err)
		}
		if cmd == nil {
			if curChunk != nil {
				curChunk.data = append(curChunk.data, line...)
			}
			continue
		}
		switch cmd.name {
		case "start":
			if curChunk != nil {
				return nil, fmt.Errorf("%d: start without preceding stop", ln)
			}
			curChunk = &chunk{
				destFile: cmd.file,
				sink:     cmd.sink,
			}
		case "stop":
			if curChunk == nil {
				return nil, fmt.Errorf("%d: stop without preceding start", ln)
			}
			chunks = append(chunks, curChunk)
			curChunk = nil
		default:
			return nil, fmt.Errorf("%d: unexpected copy command %q in source file", ln, cmd.name)
		}
	}
	if curChunk != nil {
		return nil, errors.New("missing stop at end of file")
	}
	return chunks, nil
}

// setChunkFilenames fills out the filename parts of a chunk with information about
// the source and destination.
func setChunkFilenames(chunks []*chunk, srcFile, destDir string) error {
	var err error
	for _, c := range chunks {
		c.destFile = filepath.Join(destDir, c.destFile)
		c.srcFile, err = relativePathTo(srcFile, c.destFile)
		if err != nil {
			return err
		}
	}
	return nil
}

var prefix = []byte("//copy:")

// parseCommand parses a copy command.
// If the line does not contain a command, it returns (ni, nil).
func parseCommand(line []byte) (*command, error) {
	s := bytes.TrimSpace(line)
	after, found := bytes.CutPrefix(s, prefix)
	if !found {
		return nil, nil
	}
	fields := strings.Fields(string(after))
	if len(fields) == 0 {
		return nil, errors.New("empty command")
	}

	checkArgs := func(want int) error {
		if got := len(fields) - 1; got != want {
			return fmt.Errorf("command %q should have %d args, not %d", after, want, got)
		}
		return nil
	}

	d := &command{name: fields[0]}
	switch fields[0] {
	default:
		return nil, fmt.Errorf("unknown command %q", fields[0])
	case "start":
		if err := checkArgs(2); err != nil {
			return nil, err
		}
		d.file = fields[1]
		d.sink = fields[2]
	case "stop":
		if err := checkArgs(0); err != nil {
			return nil, err
		}
	case "sink":
		// sink may have "from src1, src2, ..." after its name.
		if len(fields)-1 < 1 {
			return nil, fmt.Errorf("command %q should have at least one arg", after)
		}
		d.sink = fields[1]
	case "endsink":
		if err := checkArgs(1); err != nil {
			return nil, err
		}
		d.sink = fields[1]
	}
	return d, nil
}

// writeChunks writes the chunks to the destination files.
func writeChunks(chunks []*chunk) error {
	// Collect chunks by destination file.
	byFile := map[string][]*chunk{}
	for _, c := range chunks {
		byFile[c.destFile] = append(byFile[c.destFile], c)
	}

	for file, cs := range byFile {
		if err := writeChunksToFile(file, cs); err != nil {
			return fmt.Errorf("%s: %w", file, err)
		}
	}
	return nil
}

func writeChunksToFile(file string, chunks []*chunk) (err error) {
	// Parse the destination file into pieces.
	pieces, err := parseDestFile(file)
	if err != nil {
		return err
	}
	if err := insertChunksIntoPieces(pieces, chunks); err != nil {
		return err
	}
	data := concatPieces(pieces)
	return os.WriteFile(file, data, 0644)
}

// A piece is a contiguous section of a destination file.
// It is either literal data (sink == "") or a named sink.
type piece struct {
	srcFiles map[string]bool
	sink     string
	data     []byte
}

// parseDestFile parses a destination file into pieces.
func parseDestFile(file string) ([]*piece, error) {
	data, err := os.ReadFile(file)
	if err != nil {
		return nil, err
	}
	return parseDest(data)
}

// parseDest parses the contents of a destination file into pieces.
func parseDest(data []byte) ([]*piece, error) {
	var pieces []*piece
	lines := bytes.SplitAfter(data, []byte("\n"))
	cur := &piece{}
	for ln, line := range lines {
		cmd, err := parseCommand(line)
		if err != nil {
			return nil, fmt.Errorf("%d: %w", ln, err)
		}
		if cmd == nil {
			cur.data = append(cur.data, line...)
			continue
		}
		switch cmd.name {
		case "sink":
			// If the current piece is a sink, then we know now that it is a new sink
			// and its contents is empty; everything we've seen since the previous sink command
			// is part of a literal piece.
			if cur.sink != "" {
				pieces = append(pieces, &piece{sink: cur.sink})
				cur.sink = ""
			}
			pieces = append(pieces, cur)
			cur = &piece{sink: cmd.sink}

		case "endsink":
			if cur.sink == "" {
				return nil, fmt.Errorf("%d: endsink command without preceding sink", ln)
			}
			if cur.sink != cmd.sink {
				return nil, fmt.Errorf("%d: sink name %q does not match endsink name %q", ln, cur.sink, cmd.sink)
			}
			pieces = append(pieces, cur)
			cur = &piece{}

		default:
			return nil, fmt.Errorf("%d: unexpected copy command %q in source file", ln, cmd.name)
		}
	}
	// Same situation as in case "sink" above.
	if cur.sink != "" {
		pieces = append(pieces, &piece{sink: cur.sink})
		cur.sink = ""
	}
	return append(pieces, cur), nil
}

// insertChunksIntoPieces inserts the chunks into sink pieces of the same name.
// It returns an error if there is a chunk with no matching sink.
func insertChunksIntoPieces(pieces []*piece, chunks []*chunk) error {
	// Group chunks by sink name.
	bySink := map[string][]*chunk{}
	for _, c := range chunks {
		bySink[c.sink] = append(bySink[c.sink], c)
	}
	// For each piece with a corresponding chunk, replace the piece's contents.
	used := map[string]bool{}
	for _, p := range pieces {
		if p.sink == "" {
			continue
		}
		cs := bySink[p.sink]
		if len(cs) == 0 {
			continue
		}
		p.data = nil
		for _, c := range cs {
			p.data = append(p.data, c.data...)
			if p.srcFiles == nil {
				p.srcFiles = map[string]bool{}
			}
			p.srcFiles[c.srcFile] = true
		}
		used[p.sink] = true
	}

	// Fail if a sink with chunks wasn't used.
	for sink := range bySink {
		if !used[sink] {
			return fmt.Errorf("sink %q unused", sink)
		}
	}
	return nil
}

// concatPieces concatenates the contents of the pieces together, inserting
// markers for sinks.
func concatPieces(pieces []*piece) []byte {
	var buf bytes.Buffer
	for _, p := range pieces {
		if p.sink != "" {
			srcFiles := maps.Keys(p.srcFiles)
			slices.Sort(srcFiles)
			fmt.Fprintf(&buf, "//copy:sink %s from %s\n", p.sink, strings.Join(srcFiles, ", "))
			fmt.Fprintf(&buf, "// DO NOT MODIFY below vvvv\n")
		}
		buf.Write(p.data)
		if p.sink != "" {
			fmt.Fprintf(&buf, "// DO NOT MODIFY above ^^^^\n")
			fmt.Fprintf(&buf, "//copy:endsink %s\n", p.sink)
		}
	}
	return buf.Bytes()
}

// relativePathTo returns a path to src that is relative to dest.
// For example if src is d1/src.go and dest is d2/dest.go, then
// relativePathTo returns ../d1/src.go.
func relativePathTo(src, dest string) (string, error) {
	asrc, err := filepath.Abs(src)
	if err != nil {
		return "", err
	}
	adest, err := filepath.Abs(dest)
	if err != nil {
		return "", err
	}
	sep := string([]byte{filepath.Separator})
	ddir := filepath.Dir(adest)
	nups := 0
	for ddir != "." && ddir != sep {
		if strings.HasPrefix(asrc, ddir+sep) {
			break
		}
		ddir = filepath.Dir(ddir)
		nups++
	}
	return strings.Repeat(".."+sep, nups) + strings.TrimPrefix(asrc, ddir+sep), nil
}
