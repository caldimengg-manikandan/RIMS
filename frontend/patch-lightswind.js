const fs = require('fs');
const path = require('path');

const filesToPatch = [
  {
    path: 'node_modules/lightswind/plugin.js',
    replaces: [
      {
        target: 'syntax: "<angle>",',
        replacement: 'syntax: \'"<angle>"\','
      }
    ]
  },
  {
    path: 'node_modules/lightswind/src/styles/lightswind.css',
    replaces: [
      {
        target: 'syntax: "<angle>";',
        replacement: 'syntax: \'"<angle>"\';'
      }
    ]
  },
  {
    path: 'node_modules/lightswind/dist/components/styles/lightswind.css',
    replaces: [
      {
        target: 'syntax: "<angle>";',
        replacement: 'syntax: \'"<angle>"\';'
      }
    ]
  },
  {
    path: 'node_modules/lightswind/lightswindv1.0.css',
    replaces: [
      {
        target: 'syntax: <angle>;',
        replacement: 'syntax: \'"<angle>"\';'
      }
    ]
  }
];

console.log('Patching lightswind to fix CSS parsing errors...');

filesToPatch.forEach(fileConf => {
  const fullPath = path.resolve(__dirname, fileConf.path);
  if (fs.existsSync(fullPath)) {
    let content = fs.readFileSync(fullPath, 'utf8');
    let modified = false;

    fileConf.replaces.forEach(r => {
      if (content.includes(r.target)) {
        content = content.split(r.target).join(r.replacement);
        modified = true;
      }
    });

    if (modified) {
      fs.writeFileSync(fullPath, content, 'utf8');
      console.log(`Patched: ${fileConf.path}`);
    } else {
      console.log(`Skipped (already patched or target not found): ${fileConf.path}`);
    }
  } else {
    console.warn(`File not found: ${fileConf.path}`);
  }
});

console.log('Patching complete.');
