package genkit

import (
	"context"
	"testing"
)

func inc(_ context.Context, x int) (int, error) {
	return x + 1, nil
}

func TestActionRun(t *testing.T) {
	a := NewAction("inc", inc)
	got, err := a.Run(context.Background(), 3)
	if err != nil {
		t.Fatal(err)
	}
	if want := 4; got != want {
		t.Errorf("got %d, want %d", got, want)
	}
}
