@set the_env=patchconnect
call "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\activate.bat" "%the_env%"
call "%localappdata%\ESRI\conda\envs\%the_env%\scripts\spyder.exe" -p %cd% 
call "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\deactivate.bat"