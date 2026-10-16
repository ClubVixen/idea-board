const { app, BrowserWindow } = require('electron');
const path = require('path');
const http = require('http');
const handler = require('serve-handler');

let mainWindow;
let server;

// 1. Create a simple static server to serve index.html
// This is necessary because loading ES modules (import/export) directly 
// from file:// protocol is blocked by browsers for security.
const startServer = () => {
  server = http.createServer((request, response) => {
    return handler(request, response, {
      public: __dirname,
      headers: [
        {
          source: '**/*',
          headers: [{ key: 'Access-Control-Allow-Origin', value: '*' }]
        }
      ]
    });
  });

  server.listen(0, () => {
    const port = server.address().port;
    createWindow(port);
  });
};

// 2. Create the Desktop Window
const createWindow = (port) => {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "Detective Board",
    backgroundColor: '#09090b', // zinc-950
    icon: path.join(__dirname, 'icon.png'), // Optional: Add an icon.png to your folder
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  // Load the local server
  mainWindow.loadURL(`http://localhost:${port}/index.html`);
  
  // Remove menu bar for a cleaner look
  mainWindow.setMenuBarVisibility(false);
};

app.whenReady().then(startServer);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
  if (server) {
    server.close();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    startServer();
  }
});