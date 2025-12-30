package core

import (
	"errors"
	"testing"
)

func TestGenkitErrorUnwrap(t *testing.T) {
	original := errors.New("original failure")

	// Use INTERNAL instead of StatusInternal
	gErr := NewError(INTERNAL, "something happened: %v", original)

	// Verify errors.Is works (this is the most important check)
	if !errors.Is(gErr, original) {
		t.Errorf("expected errors.Is to return true, but got false")
	}

	// Verify Unwrap works directly
	if gErr.Unwrap() != original {
		t.Errorf("Unwrap() returned wrong error")
	}
}
