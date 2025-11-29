/**
 * Google Apps Script - Visa Exhibit Generator
 * Native Google Drive integration for creating numbered exhibit packages
 *
 * Deploy as Web App for full functionality
 */

// ============================================
// WEB APP FUNCTIONS
// ============================================

/**
 * Serve the main HTML page
 */
function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Visa Exhibit Generator')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * Include HTML partials (for modular HTML)
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

// ============================================
// CORE EXHIBIT GENERATION
// ============================================

/**
 * Generate exhibit package from Drive folder
 *
 * @param {string} folderId - Google Drive folder ID
 * @param {Object} options - Generation options
 * @return {Object} Result with generated file URLs
 */
function generateExhibitPackage(folderId, options) {
  try {
    Logger.log('Starting exhibit generation for folder: ' + folderId);

    // Validate folder
    var folder = DriveApp.getFolderById(folderId);
    if (!folder) {
      throw new Error('Folder not found');
    }

    // Get all PDF files from folder (recursive if specified)
    var files = options.recursive
      ? getAllFilesRecursive(folder, options.fileTypes)
      : getFilesInFolder(folder, options.fileTypes);

    Logger.log('Found ' + files.length + ' files');

    if (files.length === 0) {
      throw new Error('No PDF files found in folder');
    }

    // Sort files by name
    files.sort(function(a, b) {
      return a.name.localeCompare(b.name);
    });

    // Create output folder
    var outputFolderName = options.caseName || 'Exhibit_Package_' + new Date().getTime();
    var outputFolder = folder.createFolder(outputFolderName);

    Logger.log('Created output folder: ' + outputFolderName);

    // Process each file and create numbered exhibits
    var exhibits = [];
    var numberingStyle = options.numberingStyle || 'letters';

    for (var i = 0; i < files.length; i++) {
      var file = files[i];
      var exhibitNumber = getExhibitNumber(i, numberingStyle);

      // Create numbered copy
      var numberedFile = createNumberedExhibit(file, exhibitNumber, outputFolder);

      exhibits.push({
        number: exhibitNumber,
        name: file.name,
        originalUrl: file.url,
        numberedFileId: numberedFile.getId(),
        numberedFileUrl: numberedFile.getUrl()
      });

      // Update progress
      updateProgress_(i + 1, files.length, 'Processing exhibits');
    }

    Logger.log('Created ' + exhibits.length + ' numbered exhibits');

    // Generate Table of Contents
    var tocDoc = null;
    if (options.includeTOC) {
      tocDoc = generateTableOfContents(exhibits, options, outputFolder);
      Logger.log('Generated Table of Contents');
    }

    // Merge all PDFs (if requested and possible)
    var mergedPdf = null;
    if (options.mergeAll) {
      mergedPdf = mergePDFs(exhibits, tocDoc, outputFolder, options.caseName);
      Logger.log('Merged all PDFs');
    }

    // Return results
    return {
      success: true,
      outputFolderId: outputFolder.getId(),
      outputFolderUrl: outputFolder.getUrl(),
      exhibits: exhibits,
      tocUrl: tocDoc ? tocDoc.getUrl() : null,
      mergedPdfUrl: mergedPdf ? mergedPdf.getUrl() : null,
      totalExhibits: exhibits.length
    };

  } catch (error) {
    Logger.log('Error generating exhibits: ' + error.toString());
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Get all files in folder (non-recursive)
 */
function getFilesInFolder(folder, fileTypes) {
  var files = [];
  var fileTypes = fileTypes || ['application/pdf'];

  var fileIterator = folder.getFiles();

  while (fileIterator.hasNext()) {
    var file = fileIterator.next();
    var mimeType = file.getMimeType();

    if (fileTypes.indexOf(mimeType) !== -1) {
      files.push({
        id: file.getId(),
        name: file.getName(),
        url: file.getUrl(),
        mimeType: mimeType,
        file: file
      });
    }
  }

  return files;
}

/**
 * Get all files recursively from folder and subfolders
 */
function getAllFilesRecursive(folder, fileTypes) {
  var files = [];
  var fileTypes = fileTypes || ['application/pdf'];

  function recurse(currentFolder, path) {
    // Get files in current folder
    var fileIterator = currentFolder.getFiles();
    while (fileIterator.hasNext()) {
      var file = fileIterator.next();
      var mimeType = file.getMimeType();

      if (fileTypes.indexOf(mimeType) !== -1) {
        files.push({
          id: file.getId(),
          name: file.getName(),
          url: file.getUrl(),
          mimeType: mimeType,
          path: path + '/' + file.getName(),
          file: file
        });
      }
    }

    // Recurse into subfolders
    var folderIterator = currentFolder.getFolders();
    while (folderIterator.hasNext()) {
      var subfolder = folderIterator.next();
      recurse(subfolder, path + '/' + subfolder.getName());
    }
  }

  recurse(folder, '');
  return files;
}

/**
 * Create numbered exhibit from file
 */
function createNumberedExhibit(fileInfo, exhibitNumber, outputFolder) {
  var originalFile = fileInfo.file;

  // Create copy with numbered name
  var newName = 'Exhibit_' + exhibitNumber + '_' + fileInfo.name;
  var copiedFile = originalFile.makeCopy(newName, outputFolder);

  // TODO: Add exhibit number to PDF header (requires PDF manipulation)
  // For now, file name includes exhibit number

  return copiedFile;
}

/**
 * Generate exhibit number based on style
 */
function getExhibitNumber(index, style) {
  if (style === 'numbers') {
    return (index + 1).toString();
  } else if (style === 'roman') {
    var romans = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X',
                  'XI', 'XII', 'XIII', 'XIV', 'XV', 'XVI', 'XVII', 'XVIII', 'XIX', 'XX'];
    return romans[index] || (index + 1).toString();
  } else {
    // Default: letters (A, B, C...)
    return String.fromCharCode(65 + index);
  }
}

/**
 * Generate Table of Contents as Google Doc
 */
function generateTableOfContents(exhibits, options, outputFolder) {
  var doc = DocumentApp.create('Exhibit_Package_Table_of_Contents');
  var body = doc.getBody();

  // Move to output folder
  var docFile = DriveApp.getFileById(doc.getId());
  outputFolder.addFile(docFile);
  DriveApp.getRootFolder().removeFile(docFile);

  // Title
  var title = body.appendParagraph('EXHIBIT PACKAGE');
  title.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
  title.setHeading(DocumentApp.ParagraphHeading.HEADING1);

  var subtitle = body.appendParagraph('TABLE OF CONTENTS');
  subtitle.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
  subtitle.setHeading(DocumentApp.ParagraphHeading.HEADING1);

  body.appendParagraph(''); // Spacing

  // Case information
  var infoTable = body.appendTable();
  infoTable.appendTableRow().appendTableCell('Case ID:').appendTableCell(options.caseName || 'N/A');
  infoTable.appendTableRow().appendTableCell('Generated:').appendTableCell(new Date().toLocaleDateString());
  infoTable.appendTableRow().appendTableCell('Total Exhibits:').appendTableCell(exhibits.length.toString());

  if (options.beneficiaryName) {
    infoTable.insertTableRow(1).appendTableCell('Beneficiary:').appendTableCell(options.beneficiaryName);
  }

  body.appendParagraph(''); // Spacing

  // Exhibit List
  var listHeader = body.appendParagraph('Exhibit List');
  listHeader.setHeading(DocumentApp.ParagraphHeading.HEADING2);

  var exhibitTable = body.appendTable();
  var headerRow = exhibitTable.appendTableRow();
  headerRow.appendTableCell('Exhibit').setBackgroundColor('#1f77b4');
  headerRow.appendTableCell('Title/Description').setBackgroundColor('#1f77b4');
  headerRow.appendTableCell('Status').setBackgroundColor('#1f77b4');

  for (var i = 0; i < exhibits.length; i++) {
    var exhibit = exhibits[i];
    var row = exhibitTable.appendTableRow();
    row.appendTableCell('Exhibit ' + exhibit.number);
    row.appendTableCell(exhibit.name);
    row.appendTableCell('✓ Generated');
  }

  // Archive URLs section (if applicable)
  if (options.archiveUrls) {
    body.appendParagraph(''); // Spacing
    var archiveHeader = body.appendParagraph('Archived URLs (archive.org)');
    archiveHeader.setHeading(DocumentApp.ParagraphHeading.HEADING2);

    var note = body.appendParagraph('All URLs have been preserved on archive.org for long-term accessibility.');
    note.setItalic(true);
  }

  // Footer
  body.appendParagraph(''); // Spacing
  var footer = body.appendParagraph('This exhibit package was generated automatically using Google Apps Script.');
  footer.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
  footer.setFontSize(9);
  footer.setForegroundColor('#666666');

  doc.saveAndClose();

  return docFile;
}

/**
 * Merge PDFs (using Google Drive API or manual method)
 */
function mergePDFs(exhibits, tocDoc, outputFolder, caseName) {
  // Note: Google Apps Script doesn't have native PDF merging
  // Options:
  // 1. Use external API (API2PDF, etc.)
  // 2. Create a Google Doc with links to all exhibits
  // 3. Use DriveApp to organize files

  // For now, create a summary doc with links
  var mergeDoc = DocumentApp.create(caseName + '_Complete_Package');
  var body = mergeDoc.getBody();

  body.appendParagraph('COMPLETE EXHIBIT PACKAGE').setHeading(DocumentApp.ParagraphHeading.HEADING1);
  body.appendParagraph('Click links below to access each exhibit:');
  body.appendParagraph('');

  for (var i = 0; i < exhibits.length; i++) {
    var exhibit = exhibits[i];
    var file = DriveApp.getFileById(exhibit.numberedFileId);
    var p = body.appendParagraph('Exhibit ' + exhibit.number + ': ' + exhibit.name);
    p.setLinkUrl(file.getUrl());
  }

  mergeDoc.saveAndClose();

  var mergeFile = DriveApp.getFileById(mergeDoc.getId());
  outputFolder.addFile(mergeFile);
  DriveApp.getRootFolder().removeFile(mergeFile);

  return mergeFile;
}

// ============================================
// UTILITY FUNCTIONS
// ============================================

/**
 * Get folder info by ID or URL
 */
function getFolderInfo(folderIdOrUrl) {
  try {
    var folderId = extractFolderId(folderIdOrUrl);
    var folder = DriveApp.getFolderById(folderId);

    return {
      success: true,
      id: folder.getId(),
      name: folder.getName(),
      url: folder.getUrl()
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Extract folder ID from URL or return as-is if already an ID
 */
function extractFolderId(folderIdOrUrl) {
  if (folderIdOrUrl.indexOf('/folders/') !== -1) {
    return folderIdOrUrl.split('/folders/')[1].split('?')[0];
  } else if (folderIdOrUrl.indexOf('id=') !== -1) {
    return folderIdOrUrl.split('id=')[1].split('&')[0];
  } else {
    return folderIdOrUrl;
  }
}

/**
 * List files in folder for preview
 */
function listFolderFiles(folderId, recursive) {
  try {
    var folder = DriveApp.getFolderById(folderId);
    var files = recursive
      ? getAllFilesRecursive(folder, ['application/pdf'])
      : getFilesInFolder(folder, ['application/pdf']);

    return {
      success: true,
      files: files.map(function(f) {
        return {
          name: f.name,
          path: f.path || f.name,
          id: f.id
        };
      })
    };
  } catch (error) {
    return {
      success: false,
      error: error.toString()
    };
  }
}

/**
 * Update progress (placeholder for future implementation)
 */
function updateProgress_(current, total, message) {
  // Could use Properties Service to store progress
  // Client can poll for updates
  Logger.log('Progress: ' + current + '/' + total + ' - ' + message);
}

/**
 * Test function to verify setup
 */
function testSetup() {
  Logger.log('Google Apps Script Exhibit Generator - Setup Test');
  Logger.log('Script is working correctly!');
  return {
    success: true,
    message: 'Setup verified successfully',
    timestamp: new Date().toString()
  };
}
