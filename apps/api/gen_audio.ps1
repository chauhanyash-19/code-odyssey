Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SetOutputToWaveFile("d:\PhaseGuard\apps\api\synthetic_voice.wav")
$synth.Speak("Hello, this is an automated message. Your bank account has been compromised. Please share your one time password to secure it.")
$synth.Dispose()
