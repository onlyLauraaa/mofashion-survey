// =====================================================
// Google Apps Script — 问卷数据收集后端
// =====================================================
// 部署步骤:
// 1. 打开 Google Sheets，创建新表格
// 2. 扩展程序 -> Apps Script，粘贴此代码
// 3. 点击"部署" -> "新部署" -> "Web 应用"
//    执行身份: "我"，访问权限: "任何人"
// 4. 复制生成的 URL (类似 https://script.google.com/macros/s/xxx/exec)
// 5. 将此 URL 填入下面的 SCRIPT_URL，重新部署 HTML
//
// Google Sheets 列:
// A: 提交时间 | B: 问卷编号 | C: 题号 | D: 任务
// E: 兼容性选择 | F: 兼容性模型 | G: 个性化选择 | H: 个性化模型
// I: 整体偏好选择 | J: 整体偏好模型
// =====================================================

var SHEET_NAME = "Sheet1";

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);

    // 初始化表头
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(["提交时间", "问卷编号", "题号", "任务",
                       "兼容性选择", "兼容性模型", "个性化选择", "个性化模型",
                       "整体偏好选择", "整体偏好模型"]);
    }

    var timestamp = data.timestamp || new Date().toISOString();
    var surveyId = data.survey_id || "";
    var answers = data.answers || [];
    var count = 0;

    for (var i = 0; i < answers.length; i++) {
      var a = answers[i];
      sheet.appendRow([
        timestamp,
        surveyId,
        a.question || "",
        a.task || "",
        a.compat_choice || "",
        a.compat_model || "",
        a.personal_choice || "",
        a.personal_model || "",
        a.overall_choice || "",
        a.overall_model || ""
      ]);
      count++;
    }

    return ContentService
      .createTextOutput(JSON.stringify({ success: true, count: count }))
      .setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ success: false, error: err.toString() }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ status: "MoFashion Survey Backend OK" }))
    .setMimeType(ContentService.MimeType.JSON);
}
