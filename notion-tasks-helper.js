const { Client } = require('@notionhq/client');
require('dotenv').config();

const notion = new Client({ auth: process.env.NOTION_API_KEY });
const tasksDbId = process.env.NOTION_DB_TASKS;

/**
 * Оновлює статус задачі в Notion
 * @param {string} taskId - ID задачі в Notion
 * @param {string} newStatus - Новий статус ('🟢 Done', '🟡 In Progress', '🔴 Todo')
 */
async function updateTaskStatus(taskId, newStatus) {
    try {
        console.log(`🔄 Оновлюю статус задачі на "${newStatus}"...`);

        const page = await notion.pages.retrieve({ page_id: taskId });

        // Знайти властивість статусу
        let statusPropertyName = null;
        let statusPropertyType = null;
        for (const [key, value] of Object.entries(page.properties)) {
            if (value.type === 'status' || (value.type === 'select' && key === 'Status')) {
                statusPropertyName = key;
                statusPropertyType = value.type;
                break;
            }
        }

        if (!statusPropertyName) {
            throw new Error('Не знайдено властивість статусу');
        }

        // Оновити статус
        const updateProperties = {};
        if (statusPropertyType === 'status') {
            updateProperties[statusPropertyName] = {
                status: { name: newStatus }
            };
        } else {
            updateProperties[statusPropertyName] = {
                select: { name: newStatus }
            };
        }

        await notion.pages.update({
            page_id: taskId,
            properties: updateProperties
        });

        console.log(`✅ Статус оновлено на "${newStatus}"`);
        return true;
    } catch (error) {
        console.error(`❌ Помилка оновлення статусу: ${error.message}`);
        throw error;
    }
}

/**
 * Створює sub-task (дочірню задачу) в Notion
 * @param {string} title - Назва sub-task
 * @param {string} parentTaskId - ID батьківської задачі (опціонально)
 * @param {string} status - Статус ('🔴 Todo', '🟡 In Progress', '🟢 Done')
 * @param {string} priority - Пріоритет ('🔥 High', '⚡ Medium', '💤 Low')
 */
async function createSubTask(title, parentTaskId = null, status = '🔴 Todo', priority = '⚡ Medium') {
    try {
        console.log(`📝 Створюю sub-task: "${title}"...`);

        // Отримати схему database щоб дізнатися назви властивостей
        const dbInfo = await notion.databases.retrieve({
            database_id: tasksDbId
        });

        const dataSourceId = dbInfo.data_sources?.[0]?.id;
        if (!dataSourceId) {
            throw new Error('Не вдалося знайти data source ID');
        }

        // Отримати приклад задачі щоб зрозуміти структуру
        const sampleQuery = await notion.dataSources.query({
            data_source_id: dataSourceId,
            page_size: 1
        });

        if (sampleQuery.results.length === 0) {
            throw new Error('База даних порожня, неможливо визначити структуру');
        }

        const samplePage = sampleQuery.results[0];
        const properties = {};

        // Знайти назву title property
        let titlePropertyName = null;
        for (const [key, value] of Object.entries(samplePage.properties)) {
            if (value.type === 'title') {
                titlePropertyName = key;
                break;
            }
        }

        if (!titlePropertyName) {
            throw new Error('Не знайдено title властивість');
        }

        // Встановити title
        properties[titlePropertyName] = {
            title: [{ text: { content: title } }]
        };

        // Встановити статус
        for (const [key, value] of Object.entries(samplePage.properties)) {
            if (value.type === 'select' && key === 'Status') {
                properties.Status = {
                    select: { name: status }
                };
            }
            if (value.type === 'select' && key === 'Priority') {
                properties.Priority = {
                    select: { name: priority }
                };
            }
        }

        // Створити сторінку
        const response = await notion.pages.create({
            parent: { database_id: tasksDbId },
            properties: properties
        });

        console.log(`✅ Sub-task створено: ${response.id}`);
        console.log(`   URL: ${response.url}`);
        return response;
    } catch (error) {
        console.error(`❌ Помилка створення sub-task: ${error.message}`);
        throw error;
    }
}

/**
 * Логує помилку як нову задачу в Notion
 * @param {string} taskTitle - Назва задачі де сталася помилка
 * @param {Error} error - Об'єкт помилки
 * @param {string} context - Додатковий контекст помилки
 */
async function logErrorToNotion(taskTitle, error, context = '') {
    try {
        const errorTitle = `🐛 ERROR: ${taskTitle}`;
        const errorDetails = `
Error: ${error.message}
Context: ${context}
Stack: ${error.stack || 'N/A'}
Time: ${new Date().toLocaleString('uk-UA')}
        `.trim();

        console.log(`📝 Логую помилку в Notion: "${errorTitle}"...`);

        // Отримати data source ID
        const dbInfo = await notion.databases.retrieve({
            database_id: tasksDbId
        });

        const dataSourceId = dbInfo.data_sources?.[0]?.id;
        if (!dataSourceId) {
            throw new Error('Не вдалося знайти data source ID');
        }

        // Отримати структуру
        const sampleQuery = await notion.dataSources.query({
            data_source_id: dataSourceId,
            page_size: 1
        });

        if (sampleQuery.results.length === 0) {
            throw new Error('База даних порожня');
        }

        const samplePage = sampleQuery.results[0];
        let titlePropertyName = null;

        for (const [key, value] of Object.entries(samplePage.properties)) {
            if (value.type === 'title') {
                titlePropertyName = key;
                break;
            }
        }

        const properties = {
            [titlePropertyName]: {
                title: [{ text: { content: errorTitle } }]
            },
            Status: {
                select: { name: '🔴 Todo' }
            },
            Priority: {
                select: { name: '🔥 High' }
            }
        };

        // Додати notes якщо є така властивість
        for (const [key, value] of Object.entries(samplePage.properties)) {
            if (value.type === 'rich_text' && key === 'Notes') {
                properties.Notes = {
                    rich_text: [{ text: { content: errorDetails } }]
                };
            }
        }

        const response = await notion.pages.create({
            parent: { database_id: tasksDbId },
            properties: properties
        });

        console.log(`✅ Помилку залоговано в Notion: ${response.id}`);
        console.log(`   URL: ${response.url}`);
        return response;
    } catch (logError) {
        console.error(`❌ Не вдалося залогувати помилку в Notion: ${logError.message}`);
        // Не кидаємо error тут, щоб не створювати каскад помилок
    }
}

/**
 * Отримує ID задачі за назвою
 * @param {string} taskName - Назва задачі
 */
async function getTaskIdByName(taskName) {
    try {
        const dbInfo = await notion.databases.retrieve({
            database_id: tasksDbId
        });

        const dataSourceId = dbInfo.data_sources?.[0]?.id;
        if (!dataSourceId) {
            throw new Error('Не вдалося знайти data source ID');
        }

        const response = await notion.dataSources.query({
            data_source_id: dataSourceId
        });

        for (const page of response.results) {
            for (const [key, value] of Object.entries(page.properties)) {
                if (value.type === 'title' && value.title?.[0]?.plain_text) {
                    if (value.title[0].plain_text.includes(taskName)) {
                        return page.id;
                    }
                }
            }
        }

        return null;
    } catch (error) {
        console.error(`❌ Помилка пошуку задачі: ${error.message}`);
        throw error;
    }
}

module.exports = {
    updateTaskStatus,
    createSubTask,
    logErrorToNotion,
    getTaskIdByName
};
