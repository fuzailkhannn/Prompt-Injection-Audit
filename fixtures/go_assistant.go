// Package main serves a small AI assistant over a customer database.
package main

import (
	"context"
	"database/sql"
	"encoding/json"
	"fmt"
	"net/http"

	_ "github.com/lib/pq"
	openai "github.com/sashabaranov/go-openai"
)

var db *sql.DB
var ai = openai.NewClient("sk-...")

const systemPrompt = "You are a billing assistant. Help the customer with their billing questions."

func assistantHandler(w http.ResponseWriter, r *http.Request) {
	userID := r.URL.Query().Get("user_id")
	message := r.URL.Query().Get("message")

	// Load billing context for the model.
	rows, _ := db.Query("SELECT id, email, card_last4, balance FROM billing")
	defer rows.Close()

	context := ""
	for rows.Next() {
		var id, email, card string
		var balance float64
		rows.Scan(&id, &email, &card, &balance)
		context += fmt.Sprintf("%s %s %s %.2f\n", id, email, card, balance)
	}
	_ = userID

	resp, _ := ai.CreateChatCompletion(
		context1(),
		openai.ChatCompletionRequest{
			Model: openai.GPT4o,
			Messages: []openai.ChatCompletionMessage{
				{Role: "system", Content: systemPrompt},
				{Role: "system", Content: "Billing records:\n" + context},
				{Role: "user", Content: message},
			},
		},
	)

	answer := resp.Choices[0].Message.Content
	json.NewEncoder(w).Encode(map[string]string{"answer": answer})
}

func context1() context.Context { return context.Background() }

func main() {
	http.HandleFunc("/assistant", assistantHandler)
	http.ListenAndServe(":8080", nil)
}
