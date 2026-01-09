from menu_ai import ai
from menu_schemas import AnswerOutputSchema, MenuItemSchema, MenuQuestionInputSchema
from pydantic import BaseModel, Field

from genkit.blocks.document import Document
from .prompts import s04_ragDataMenuPrompt

class IndexMenuItemsOutputSchema(BaseModel):
    rows: int = Field(...)

@ai.flow(name='s04_indexMenuItems')
async def s04_indexMenuItemsFlow(
    menu_items: list[MenuItemSchema],
) -> IndexMenuItemsOutputSchema:
    documents = []
    for item in menu_items:
        text = f'{item.title} {item.price} \n {item.description}'
        documents.append(Document.from_text(text, metadata=item.model_dump()))
    
    await ai.index(
        indexer='menu-items',
        documents=documents,
    )
    return IndexMenuItemsOutputSchema(rows=len(menu_items))


@ai.flow(name='s04_ragMenuQuestion')
async def s04_ragMenuQuestionFlow(
    my_input: MenuQuestionInputSchema,
) -> AnswerOutputSchema:
    # Retrieve the 3 most relevant menu items for the question
    docs = await ai.retrieve(
        retriever='menu-items',
        query=my_input.question,
        options={'k': 3},
    )
    
    menu_data = [doc.metadata for doc in docs.documents]

    # Generate the response
    response = await s04_ragDataMenuPrompt(
        {'menuData': menu_data, 'question': my_input.question}
    )
    return AnswerOutputSchema(answer=response.text)
