interface AppSpeechRecognitionResultItem {
  transcript: string
  confidence: number
}

interface AppSpeechRecognitionResult {
  readonly length: number
  readonly isFinal: boolean
  [index: number]: AppSpeechRecognitionResultItem
}

interface AppSpeechRecognitionResultList {
  readonly length: number
  [index: number]: AppSpeechRecognitionResult
}

interface AppSpeechRecognitionEvent extends Event {
  readonly resultIndex: number
  readonly results: AppSpeechRecognitionResultList
}

interface AppSpeechRecognitionErrorEvent extends Event {
  readonly error: string
}

interface AppSpeechRecognition extends EventTarget {
  continuous: boolean
  interimResults: boolean
  lang: string
  start(): void
  stop(): void
  onresult: ((event: AppSpeechRecognitionEvent) => void) | null
  onerror: ((event: AppSpeechRecognitionErrorEvent) => void) | null
  onend: (() => void) | null
}

interface Window {
  SpeechRecognition?: new () => AppSpeechRecognition
  webkitSpeechRecognition?: new () => AppSpeechRecognition
}