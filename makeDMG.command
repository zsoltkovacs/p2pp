
python3 setup.py py2app
hdiutil create dist/p2pp.dmg -ov -volname "p2ppInstaller" -fs HFS+ -srcfolder "dist"
rm /Users/tomvandeneede/Dropbox/Public/p2pp.dmg
hdiutil convert dist/p2pp.dmg -format UDZO -o /Users/tomvandeneede/Dropbox/Public/p2pp.dmg
rm dist/p2pp.dmg
