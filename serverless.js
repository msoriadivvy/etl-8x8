const path = require("path");
const minimist = require("minimist");
const yaml = require("yaml-boost");

module.exports = yaml.load(path.join(__dirname, "serverless.core.yml"), minimist(process.argv));
