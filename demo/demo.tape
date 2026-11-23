# Recorded by .github/workflows/demo.yml — real server, real sandbox, real output.
Output docs/demo.gif

Set Shell "bash"
Set FontSize 15
Set Width 1180
Set Height 760
Set Padding 24
Set Theme "GitHub Dark"
Set TypingSpeed 45ms

# Pull the image and start the sandbox off-camera, so the recording shows normal speed.
Hide
Type "python demo/demo.py --warmup && clear" Enter
Wait@300s
Show

Sleep 500ms
Type "python demo/demo.py"
Sleep 400ms
Enter
Wait+Screen@180s /real calls/
Sleep 4s
