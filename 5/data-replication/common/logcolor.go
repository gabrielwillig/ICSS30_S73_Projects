package common

import "log"

const (
	ColorReset  = "\033[0m"
	ColorRed    = "\033[31m"
	ColorGreen  = "\033[32m"
	ColorYellow = "\033[33m"
)

func Info(format string, v ...interface{}) {
	log.Printf(ColorGreen+format+ColorReset, v...)
}

func Warn(format string, v ...interface{}) {
	log.Printf(ColorYellow+format+ColorReset, v...)
}

func Error(format string, v ...interface{}) {
	log.Printf(ColorRed+format+ColorReset, v...)
}
